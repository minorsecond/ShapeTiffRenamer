__author__ = 'td27097'
"""
Rename shape and image files to match for ERDAS Imagine processing
Ross Wardrup
"""

import sys
from os import walk, makedirs, path
from os.path import join, splitext, exists, dirname, realpath
from shutil import copyfile
from sys import exit, argv
from functools import partial
import pyproj
from gui import *
import logging
from uuid import uuid4
import datetime
import gdal
import ogr
import ntpath
from models import SpatialiteDb
from sqlalchemy import create_engine, MetaData, exc
import base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, create_session, relationship
from shapely.geometry import Polygon, Point  # For centroid calculation
from shapely.ops import transform
# TODO: Incorporate gdaladdo to build pyramids

TEST = False
DB_FILENAME = 'str.db'

class GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):

        super(GUI, self).__init__()

        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setFixedSize(800, 185)  # no resizing
        self.output_text = ''
        self.image_root_set = False
        self.shp_root_set = False
        self.working_directory_set = False
        self.db_output_path = None

        # Handle button clicks on Build DB tab
        self.BrowseForDbOutput.clicked.connect(self.handle_buildDb_db_browse_button)
        self.BrowseForImageRoot.clicked.connect(self.handle_ImageRoot_browse_button)
        self.BrowseForShapeRoot.clicked.connect(self.handle_shapeRoot_browse_button)
        self.CreateDbButton.clicked.connect(self.handle_create_db_button)

        # Handle button clicks in copy/rename data tab
        #self.ClearButton.clicked.connect(self.handle_tab2_clear_button)
        self.ProcessButton.clicked.connect(self.handle_tab2_process_button)
        self.BrowseForImageDir.clicked.connect(self.handle_img_root_browse)
        self.BrowseForOutputDir.clicked.connect(self.handle_output_dir_browse)
        self.BrowseForDb.clicked.connect(self.handle_db_browse)

        self.all_files = 0
        self.total_files = 0
        self.files_left = 0
        self.files_processed = 0

    def handle_buildDb_db_browse_button(self):
        """
        Handle browsing for db output path
        :return:
        """
        self.db_output_path = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.DbOutputPath.setText(self.db_output_path)
        self.DbFileInputEdit.setText(self.db_output_path)

    def handle_ImageRoot_browse_button(self):
        """
        Handle browsing for image root
        :return:
        """

        self.img_root_path = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ImageRootDirEdit.setText(self.img_root_path)

    def handle_shapeRoot_browse_button(self):
        """
        handle browsing for shape root
        :return:
        """

        self.shp_root_path = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ShapeRootEdit.setText(self.shp_root_path)

    def handle_create_db_button(self):
        """
        Handles clicking db create button
        :return:
        """
        self.image_extension = self.ImageTypeCombo.currentText()
        if self.db_output_path and self.shp_root_path and self.img_root_path:
            db_io = DatabaseIo((self.img_root_path, self.image_extension,
                                self.shp_root_path), self.db_output_path)
            db_io.build_database()


    def handle_tab2_clear_button(self):
        """
        Handles the clear button clicked event
        """

        self.ImageRootInputEdit.clear()
        self.ShapeRootInputEdit.clear()
        self.OutputDirectoryEdit.clear()
        self.OutputWindow.clear()
        self.ProcessButton.setText("Process")

    def handle_tab2_process_button(self):
        """
        Handles the process button clicked event
        """

        # Get parameters from GUI
        self.image_extension = self.ImageTypeCombo.currentText()
        image_path = self.ImageDirInput.text()
        self.working_directory = self.OutputDirectoryEdit.text()

        self.session = init_db(self.DbFileInputEdit.text())

        payload = (image_path, None, self.working_directory, self.image_extension)

        self.ProcessButton.setText("Processing")
        self.ProcessButton.setDisabled(True)
        if len(self.ImageDirInput.text()) > 0 and len(self.OutputDirectoryEdit.text()) > 0 \
                and len(self.DbFileInputEdit.text()) > 0:
            runner(payload)

            self.create_new_filenames()

            logging.info("- Finished at {}".format(get_datetime()))
            text = "\n-- Image/Shp processing complete at {} --".format(get_datetime())

            if not TEST:
                self.ProcessButton.setEnabled(True)
                self.ProcessButton.setText("Process")

            print("\n** Finished at {} **".format(get_datetime()))

    def handle_img_root_browse(self):
        """
        Handles user clicking browse for image root path
        """

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ImageDirInput.setText(openfile)

    def handle_shp_root_browse(self):
        """
        Handles user clicking browse for shp root path
        """

        self.shp_root_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ShapeRootInputEdit.setText(openfile)

    def handle_output_dir_browse(self):
        """
        Handles user clicking browse for output dir
        """

        self.working_directory_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        print(openfile)
        self.OutputDirectoryEdit.setText(openfile)

    def handle_db_browse(self):
        """
        Handles clicking the db location browse
        :return:
        """

        openfile = QtWidgets.QFileDialog.getOpenFileName(self)
        try:
            self.DbFileInputEdit.setText(openfile[0])
        except AttributeError as e:
            print("*** ERROR: {0} ***".format(e))
            logging.ERROR(e)

    def done(self):
        """
        Updates the output window when finished.
        """

        self.ProcessButton.setEnabled(True)
        app.processEvents()

    def create_new_filenames(self):
        """
        rename image and shape files
        :param paths: tuple. first is image path, second is shp path
        :return: Tuple (orig path, new path, id)
        """
        destination = join(self.working_directory, "output")
        shapes_data = {}
        imagery_data = {}
        error_status = False
        files = []
        matched_files = {}
        match = []
        image_paths = []
        shape_paths = []
        image_ids = []
        step = None
        extensions_to_search = []
        copier_payload = []
        shp_extensions = ('.shp', '.dbf', '.shx', '.prj')

        # Test if destination is actually a path first
        if exists(destination):
            if self.image_extension == '.img':
                extensions_to_search.append(".ige")
                extensions_to_search.append(".rrd")

            if exists(self.DbFileInputEdit.text()):  # If the db exists
                print("* Database file found. Using stored data")
                shapes = SpatialiteDb.Shapes
                images = SpatialiteDb.Imagery
                # We will load the db rows here
                session = init_db(self.DbFileInputEdit.text())

                # Make sure DB was completely built before going ons
                _shp = session.query(shapes).order_by(shapes.id.desc()).first()
                _img = session.query(images).order_by(images.id.desc()).first()
                if _shp.uuid == 'COMPLETE':
                    print("* Loading shape data into RAM...")
                    for p in session.query(shapes):
                        if p.uuid != "COMPLETE":
                            shape_id = p.id
                            shape_uuid = p.uuid
                            shape_last_access = p.last_access
                            shape_original_path = p.original_path
                            shape_output_path = p.output_path
                            shape_centroid = p.centroid
                            shape_centroid_split = shape_centroid.split(',')
                            shape_centroid = [shape_centroid_split[0], shape_centroid_split[1]]

                            shape_data = (shape_id, shape_uuid, shape_last_access, shape_original_path,
                                          shape_output_path, shape_centroid)

                            # Add to a dict for processing
                            shapes_data[shape_uuid] = shape_data

                else:
                    input("*** ERROR: The database was not completely built. Delete the .db file and"
                          "run again ***")

                if _img.uuid == 'COMPLETE':
                    print("* Loading imagery into RAM...")
                    for p in session.query(images):
                        print(self.ImageDirInput.text())
                        print(p.original_path)
                        if p.uuid != "COMPLETE" and self.ImageDirInput.text() in p.original_path:
                            image_id = p.id
                            image_uuid = p.uuid
                            image_last_access = p.last_access
                            image_original_path = p.original_path
                            image_output_path = p.output_path
                            image_centroid = p.centroid
                            if image_centroid:
                                image_centroid_split = image_centroid.split(',')
                                image_centroid = [image_centroid_split[0], image_centroid_split[1]]
                            else:
                                image_centroid = None

                            image_data = (shape_id, shape_uuid, shape_last_access, shape_original_path,
                                          shape_output_path, image_centroid)

                            imagery_data[image_uuid] = image_data

                else:
                    input("*** ERROR: The database was not completely built. Delete the .db file and"
                          "run again ***")
                    error_status = True

                if not error_status:
                    print("* Testing shapes and rasters for spatial correlation...")
                    # search each image
                    for image_uuid, image_data in imagery_data.items():
                        best_distance = None
                        best_match = None
                        matched_image = session.query(images).filter_by(uuid=image_uuid).first()

                        # If image is alreated matched, skip it
                        if not matched_image.matched_to:
                            # Iterate over every shape for each image
                            for shape_uuid, shape_data in shapes_data.items():

                                # Calculat the distance between the two centroids
                                if shape_data[5] and image_data[5]:
                                    current_distance = distance_between_centroids(shape_data[5], image_data[5])

                                    # Iteratively calculate the closest match and add it to the best_match var
                                    if best_distance:
                                        if current_distance < best_distance:
                                            best_distance = current_distance
                                            best_match = shape_uuid
                                    else:
                                        best_distance = current_distance
                                        best_match = shape_uuid

                                else:
                                    # If neither image nor shape have a centroid calculated,
                                    # give it a null value for the match field.
                                    best_match = None

                            # Assign the best_match to the image currently being processed
                            matched_image.matched_to = best_match
                            session.commit()

                        else:
                            best_match = matched_image.matched_to

                        matched_files[image_uuid] = best_match

                    # Move on to parsing/renaming the filenames
                    print("* Parsing files...")
                    for image_uuid, shape_uuid in matched_files.items():
                        list_index_counter = 0

                        # Query the DB
                        image = session.query(images).filter_by(uuid=image_uuid).first()
                        shapefile = session.query(shapes).filter_by(uuid=shape_uuid).first()

                        # Parse the imagery filenames
                        image_path = image.original_path  # Store the original image path
                        image_file = ntpath.basename(image_path)  # Get the current image filename only
                        image_extension = splitext(image_path)[1]  # Get the extension of the current image
                        image_filename_list = listify_filename(image_file)  # Break the filname into a list

                        # Get the first item in the list and assign it as the image ID var
                        image_sid = image_filename_list[0]

                        # Now we determine the image type (pansharpened vs panchromatic)
                        if "PAN" in image_filename_list or "pan" in image_filename_list:
                            image_type = 'PAN'              # Assign it type "PAN"

                            # Set the destination path based on user input, placing the file in the "PAN"
                            # directory created by this tool
                            image_type_destination = join(destination, 'PAN')

                            # Create the new image path based on its type and user destination directory
                            # input
                            new_image_path = join(image_type_destination, "{0}_{1}{2}"
                                                .format(image_sid, image_type, image_extension))

                        # Do all of the same for pansharpened
                        elif 'PSH' in image_filename_list or "psh" in image_filename_list:
                            image_type = 'PSH'
                            image_type_destination = join(destination, 'PSH')  # set shp dest path

                            new_image_path = join(image_type_destination, "{0}_{1}{2}"
                                                .format(image_sid, image_type, image_extension))

                        # If we can't categorize the image based on the "PAN" and "PSH" types, place the
                        # image in the "uncategorized" directory created by this tool, and write a warning
                        # to the log
                        else:
                            image_type = 'Uncategorized'
                            image_type_destination = join(destination, 'uncategorized_images')
                            text = "- Could not categorize image {}"\
                                .format(image)
                            logging.warning(text)
                            print(text)

                            new_image_path =  join(image_type_destination, "{0}{1}"
                                                .format(image_file, image_extension))

                        # Parse the fhape filenames
                        if shapefile:
                            shape_path = shapefile.original_path  # Store the original shapefile path
                            shape_file = ntpath.basename(shape_path)  # Get the shapefile name
                            shape_name = ntpath.basename(shape_path)[0]  # Get the shapefile name less the ext
                            shape_extension = splitext(shape_path)[1]  # Get the shapefile extension

                            # Break the shapefile name into a list
                            shape_filename_list = listify_filename(shape_file)

                        else:
                            shape_path = None

                        # Create a tuple containing copy information for the file_copier function. The
                        # Tuple contains the data:
                        # (original_image_path, image_type, new_image_path, original_shp_path, image_id)
                        files_to_copy = (image_path, image_type, new_image_path, shape_path, image_sid)

                        # Add the tuple to a list of tuples that file_copier will iterate through
                        copier_payload.append(files_to_copy)

                    text = "\t - Copying {}".format(step)

                    # If we have any files to copy, run the copier
                    if len(copier_payload) > 0 and error_status == False:
                        file_copier(copier_payload, destination)  # copy the files

        else:
            text = ("- WARNING: destination directory {} does not exist and I "
                    "couldn't create it for you. "
                    "Did you enter a valid path?".format(destination))

            logging.warning(text)


def runner(payload):
        """
        Runs the entire thing
        :return:
        """

        gui = GUI()
        session = None

        if not TEST:
            gui.ProcessButton.setDisabled(True)

            image_path = payload[0]
            shp_path = payload[1]
            working_directory = payload[2]
            image_extension = payload[3]

        else:
            image_path = "E:\\scriptTest\\input\\image\\subset"
            shp_path = "E:\\scriptTest\\GIS_FILES"
            working_directory = "E:\\scriptTest\\output"
            image_extension = ".img"

        # set up logfile
        logfile = join(working_directory, 'renamer.log')

        logging.basicConfig(filename=logfile,
                            format='%(asctime)s %(levelname)s %(message)s',
                            level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                            filemode="w")

        logging.info("- image path: {0}, shp path: {1}, working directory: "
                     "{2}".format(image_path, shp_path, working_directory))

        paths = (image_path, shp_path)

        # Create the directories relative to user's working directory
        output_dir = join(working_directory, "output")
        directories = (output_dir, join(output_dir, 'PSH'),
                       join(output_dir, 'PAN'),
                       join(output_dir, 'uncategorized_images'),
                       join(output_dir, 'shp'))

        print("* Creating directories...")
        for directory in directories:
            directory_creator(directory)


def listify_filename(filename):
    """
    Breaks apart filenames into lists
    :return:
    """

    file = filename.replace('-', '_')  # replace hyphens with underscore
    file = file.replace('.', '_')  # replace periods with underscore
    file = file.split('_')  # split at underscores to create list

    return file


def match_shp_to_image(shp_filename_values, image_ids):
    """
    Finds shapefiles that match image files, by name
    :param shp_filename_values: array containing split strings in shp filename
    :param image_ids: tuple of image names
    :return: matched id (string)
    """

    sid = None

    for image_id in image_ids:
        if 'PIXEL' in shp_filename_values:
            for value in shp_filename_values:
                if value.isdigit() and len(value) == 12:
                    if value == image_id:
                        sid = value  # try to match shp id to image id
    return sid


def create_manifest(destination, data):
    """
    Create list of input/output files
    """

    file = join(destination, 'manifest.txt')

    time = get_datetime()

    with open(file, "a") as manifest_file:
        manifest_file.write('- {0}: copied from {1} written to {2}\n'
                            .format(time, data[1], data[0]))


def file_copier(data, destination):
    """
    Copies files from source to destination
    :param data: list of tuples containing (image_path, image_type, new_image_filename, shape_path, image_sid)
    :return: IO
    """
    shapefile_count = 0
    image_count = 0

    print("* Copying files...")

    if exists(destination):
        for item in data:  # copy each file

            image_path = item[0]  # Original image path
            image_name = ntpath.basename(item[0])  # Original image filename only
            image_type = item[1]  # Image type (PSH or PAN) - to be appended to shapefile
            image_destination = item[2]  # Image destination path
            new_image_name = ntpath.basename(item[2])  # new_image_filename only

            if item[3]:
                shpdir = dirname(realpath(item[3]))  # directory of original shapefile
                shape_name = (ntpath.basename(item[3]))  # Get original shapefile name only
                _shape_output_name = item[4]  # image_sid to use for the new shapefile name

                # Build name for shape data
                shapefile_to_copy = []
                shp_extensions = ('.shp', '.dbf', '.shx', '.prj')

                for extension in shp_extensions:

                    # Build list of files to copy

                    # Get name of  original shapefile and its associated data files
                    file = "{0}{1}".format(splitext(shape_name)[0], extension)
                    to_copy = join(shpdir, file)  # Build the original path
                    shapefile_to_copy.append(to_copy)  # Add original shp paths to a list to copy from

                    # Build new shapefile names and new paths
                    shape_output_name = "{0}_{1}{2}".format(_shape_output_name, image_type,extension)
                    new_shapefile_path = join(destination, "shp")
                    new_shapefile_path = join(new_shapefile_path, shape_output_name)  # fullp ath

                    # Copy the shapefiles to the new shapefile path
                    copyfile(to_copy, new_shapefile_path)

                    logging.info("- Copied shapefile {0} to {1}"
                                 .format(shapefile_to_copy, new_shapefile_path))

                    create_manifest(destination, (item[3], new_shapefile_path))
                    shapefile_count += 1

                    print(" - Copied shapefile {0} of {1}".format(shapefile_count, len(data) * 4))

            if not exists(image_destination):

                # If the image file doesn't already exist in destination, copy it.
                # TODO: Use checksum to copy image if it doesn't match the original

                try:
                    copyfile(image_path, image_destination)

                    logging.info("- Copied file {0} to {1}".format(image_path, image_destination))
                    create_manifest(destination, (image_path, image_destination))

                    image_count += 1
                    print("\n - Copied image {0} of {1}".format(image_count, len(data)))

                except FileNotFoundError:
                    text = "*** ERROR: File {} in database but not found in filesystem. It may " \
                           "have  been deleted"
                    logging.error(text)
                    print(text)

                # Check if ide and rrd files exist, and copy them over if they do
                for extension in ('.ige','.rrd', '.rde'):
                    additional_file = "{0}{1}".format(splitext(image_name)[0], extension)
                    additional_file_destination_name = "{0}{1}".format(new_image_name, extension)
                    additional_file_path = join(dirname(realpath(image_path)), additional_file)
                    additional_file_destination_path = join(dirname(realpath(image_destination)),
                                                            additional_file)

                    if exists(additional_file_path):
                        copyfile(additional_file_path, additional_file_destination_path)
                        create_manifest(destination, (additional_file_path,
                                                      additional_file_destination_path))
                        print("\t* Copied additional {} file".format(extension))
            else:
                text = ("- File {} already exists in destination. "
                        "Not copying.".format(file[1]))
                logging.warning(text)

    else:
        text = ("- Directory {} does not exist and I could "
                "not create it.".format(destination))
        logging.warning(text)


def check_for_duplicates(files_to_check):
    """
    Checks for duplicates
    :param files_to_check: tuple containing split filenames
    :return: bool
    """

    file_name_list = []
    count_dict = {}

    error_status = False

    for file in files_to_check:
        file_name_list.append(file[2])
        count_dict[file[0]] = file_name_list.count(file[2])

    for filename, count in count_dict.items():
        if count > 1:
            text = ("- ERROR: Duplicate filename {}".format(filename))
            logging.error(text)

            error_status = True

    return error_status


def init_db(path):
    """
    Creates and initializes the db at path
    :param path: string denoting db directory
    :return: DB file
    """


    if ntpath.basename(path) == DB_FILENAME:
        db_path = path
    else:
        db_path = join(path, DB_FILENAME)
    # Create the session

    engine = create_engine('sqlite:///{}'.format(db_path))
    base.Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    return session


def write_shape_row(session, data):
    """
    Writes a row to the shapefile table
    :param data: data to write
    :return: DB IO
    """

    for uuid, data in data.items():
        shape_uuid = uuid
        shape_original_path = data[0]
        shape_new_path = data[1]
        shape_timestamp = data[2]  # time shape was moved
        shape_centroid = data[3]

        shape_row = SpatialiteDb.Shapes

        new_shape = shape_row(uuid = shape_uuid,
                              last_access = datetime.datetime.now(),
                              original_path = shape_original_path,
                              output_path = shape_new_path,
                              centroid = shape_centroid)

        try:
            session.add(new_shape)
            session.commit()

        except Exception as e:
            print(e)

def write_image_row(session, data):
    """
    Writes a row to the shapefile table
    :param data: data to write
    :return: DB IO
    """

    for uuid, data in data.items():
        image_uuid = uuid
        image_original_path = data[0]
        image_new_path = data[1]
        image_timestamp = data[2]  # time shape was moved
        image_centroid = data[3]

        image_row = SpatialiteDb.Imagery
        new_image = image_row(uuid = image_uuid,
                             last_access = datetime.datetime.now(),
                             original_path = image_original_path,
                             output_path = image_new_path,
                             centroid = image_centroid)

        try:
            session.add(new_image)
            session.commit()

        except Exception as e:
            print(e)


class DatabaseIo:
    """
    Methods for storing and reading from spatialite db. Populating a spatialite db will allow for
    much faster processing if there are multiple iterations.
    """

    def __init__(self, paths, db_path):
        """
        Initialize the class
        """

        # Define the variables
        self.engine = None
        self.DBSession = None
        self.session = None
        self.metadata = None
        self.data_paths = paths
        self.db_path = db_path

    def build_database(self):
        """
        Builds the database with data
        """

        # Create the DB rows

        # List of tuples that contain (image_filename, shape_filename)

        # Generate list of filepaths to imagery and shapedata. These lists need to be kept
        # in memory so that if the user chooses that the output be placed into a subdirectory
        # of the input directory, the files output by this tool will not be mistaken as more
        # original input files, causing a neverending loop.

        self.image_data = {}  # tmp storage dicts for each db write iteration
        self.shape_data = {}
        self.session = init_db(self.db_path)
        self.image_root_path = self.data_paths[0]
        self.image_extension = self.data_paths[1]
        self.shape_root_path = self.data_paths[2]

        self.image_paths = []
        self.shape_paths = []

        print("* Adding images to database...")
        for (dirpath, dirnames, filenames) in walk(self.image_root_path):
            if "output" not in dirpath and "img_conversions" not in dirpath:
                for file in filenames:
                    if self.image_extension == '.img':
                        self.image_extension = ['.img', '.rrd', '.ige', 'rde']
                    if splitext(file)[1] in self.image_extension:  # Only catch image files
                        image_path = join(dirpath, file)
                        self.image_paths.append(image_path)
                        image_uuid = uuid4().hex  # UUID for DB

                        if splitext(file)[1] not in ['.ige', '.rde', '.rrd']:
                            try:
                                self.image_functions = ImageReader(image_path)
                                _, image_centroid = self.image_functions.image_bounds()
                                image_centroid = "{0},{1}".format(image_centroid.x, image_centroid.y)
                            except:
                                image_centroid = None

                        else:
                            image_centroid = None

                        self.image_data[image_uuid] = (image_path, None, get_datetime(),
                                                       image_centroid)
                        write_image_row(self.session, self.image_data)
                        self.image_data = {}  # erase the dict

        # write completion stub
        self.image_data['COMPLETE'] = ('COMPLETE', 'COMPLETE', 'COMPLETE', 'COMPLETE')
        write_image_row(self.session, self.image_data)

        print("* Completed writing imagery data to database.")

        print("* Adding shape data to database...")
        for (dirpath, dirnames, filenames) in walk(self.shape_root_path):
            for file in filenames:
                if splitext(file)[1] == '.shp' and 'PIXEL' in file:  # OGR opens .shp extension
                    shape_path = join(dirpath, file)
                    self.shape_paths.append(shape_path)
                    shape_uuid = uuid4().hex  # UUID for DB

                    try:
                        self.shape_functions = ShapeReader(shape_path)
                        _, shape_centroid = self.shape_functions.shapefile_bounds()
                        shape_centroid = "{0},{1}".format(shape_centroid.x, shape_centroid.y)

                    except Exception as e:
                        print(e)
                        shape_centroid = None

                    self.shape_data[shape_uuid] = (shape_path, None, get_datetime(), shape_centroid)

                    write_shape_row(self.session, self.shape_data)
                    self.shape_data = {}  # erase the dict

        # write completion stub
        self.shape_data['COMPLETE'] = ('COMPLETE', 'COMPLETE', 'COMPLETE', 'COMPLETE')
        write_shape_row(self.session, self.shape_data)

        print("* Completed writing shape data to database.")


class ShapeReader:
    """
    Members for reading shapefiles
    """

    def __init__(self, shape_path):
        self.shape_path = shape_path

    def read_shapefile(self):
        """
        Reads the shapefile
        """

        self.vector = ogr.Open(self.shape_path)
        self.layer = self.vector.GetLayer()
        self.feature = self.layer.GetFeature(0)

    def shapefile_bounds(self):
        """
        Gets the shapefile bounds (actual, not bb)
        """
        self.read_shapefile()
        self.vector_geometry = self.feature.GetGeometryRef()
        self.shape_origin = self.shapefile_centroid()

        return self.vector_geometry, self.shape_origin

    def shapefile_centroid(self):
        """
        Gets the shapefile centroid
        """
        self.polygon_points = []
        ring = self.vector_geometry.GetGeometryRef(0)
        points = ring.GetPointCount()

        # Build a list of points
        for point in range(points):
            lon, lat, z = ring.GetPoint(point)

            point = Point(lon, lat)
            self.polygon_points.append(point)

        # Recreate the polygon using Shapely, and then calculate the centroid
        polygon = Polygon([[p.x, p.y] for p in self.polygon_points])
        polygon_centroid = Point(polygon.centroid)

        return polygon_centroid


class ImageReader:
    """
    Contains methods for reading imagery for processing
    """

    def __init__(self, image_path):
        """
        Initialize the class
        """
        self.image = None
        self.image_path = image_path

    def read_image(self):
        """
        Read the geotiff using GDAL
        """

        self.image = gdal.Open(self.image_path)

    def image_bounds(self):
        """
        Get the geotiff bounding box
        """
        self.read_image()

        self.transform = self.image.GetGeoTransform()

        # Get raster properties
        self.pixelWidth = self.transform[1]
        self.pixelHeight = abs(self.transform[5])
        self.cols = self.image.RasterXSize
        self.rows = self.image.RasterYSize

        # Get the vertex coordinates
        self.x_left = self.transform[0]
        self.y_top = self.transform[3]
        self.x_right = self.x_left + self.cols * self.pixelWidth
        self.y_bottom = self.y_top - self.rows * self.pixelHeight

        # Create a shape using the vertex coordinates
        self.ring = ogr.Geometry(ogr.wkbLinearRing)
        self.ring.AddPoint(self.x_left, self.y_top)
        self.ring.AddPoint(self.x_left, self.y_bottom)
        self.ring.AddPoint(self.x_right, self.y_top)
        self.ring.AddPoint(self.x_right, self.y_bottom)
        self.ring.AddPoint(self.x_left, self.y_top)

        # Add the shape to a geometry
        self.raster_geometry = ogr.Geometry(ogr.wkbPolygon)
        self.raster_geometry.AddGeometry(self.ring)

        self.image_origin = self.image_centroid()

        return self.raster_geometry, self.image_origin

    def image_centroid(self):
        """
        Gets the image centroid
        """

        self.polygon_points = []

        ring = self.raster_geometry.GetGeometryRef(0)
        points = ring.GetPointCount()

        # Build a list of points
        for point in range(points):
            lon, lat, z = ring.GetPoint(point)

            point = Point(lon, lat)
            self.polygon_points.append(point)

        # Recreate the polygon using Shapely, and then calculate the centroid
        polygon = Polygon([[p.x, p.y] for p in self.polygon_points])
        raster_centroid = Point(polygon.centroid)

        return raster_centroid


def distance_between_centroids(shape, image):
    """
    Checks the distance between two polygon objects using Shapely
    :param object_a: Shapely Point object
    :param object_b: Shapely Point Object
    :return: distance
    """

    if shape[0] and shape[1] and image[0] and image[1]:
        point_a = Point(float(shape[0]), float(shape[1]))
        point_b = Point(float(image[0]), float(image[1]))

        return point_a.distance(point_b)


def directory_creator(directory_to_create):
    """
    Creates working directory
    :param directory_to_create: string pointing to new directory
    :return: IO
    """

    if not exists(directory_to_create):
        makedirs(directory_to_create)


def get_datetime():
    """
    Gets pretty datetime
    :return: datetime in string format
    """

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def intersect_shape_and_tif(image_path, shape_path):
    """
    Checks to see if image intersects shape
    :param image_path: Path to image file
    :param shape_path: Path to shapefile
    :return: bool
    """

    # Instantiate the classes
    shape_functions = ShapeReader(shape_path)
    image_functions = ImageReader(image_path)

    # Get feature, layer and centroids for each
    feature, feature_centroid = shape_functions.shapefile_bounds()
    layer, layer_centroid = image_functions.image_bounds()

    return layer.Intersect(feature), feature_centroid, layer_centroid


def main():
    """
    Fire off the tool
    :return:
    """

    # Start GUI
    app = QtWidgets.QApplication(argv)
    window = GUI()
    if not TEST:
        window.show()
        exit(app.exec_())

    else:
        runner(None)

if __name__ == '__main__':
    if TEST:
        print("*** TESTING MODE. REMOVE TEST FLAG ***")
        app = None

    main()
