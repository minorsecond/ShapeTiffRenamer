"""
Rename shape and image files to match for ERDAS Imagine processing
Ross Wardrup
"""

# TODO: Add lowercase "pan" and "psh" to the search lists.

import sys
from hashlib import sha1
from os import walk, makedirs, path
from os.path import join, splitext, exists
from shutil import copyfile
from sys import exit, argv
from gui import *
import logging
import datetime

TEST = True


class GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):

        super(GUI, self).__init__()

        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setFixedSize(800, 140)  # no resizing
        self.output_text = ''
        self.image_root_set = False
        self.shp_root_set = False
        self.working_directory_set = False

        self.ProcessButton.setDisabled(True)

        # Handle button clicks in copy/rename data tab
        self.ClearButton.clicked.connect(self.handle_tab1_clear_button)
        self.ProcessButton.clicked.connect(self.handle_tab1_process_button)
        self.BrowseForImageRoot.clicked.connect(self.handle_img_root_browse)
        self.BrowseForShapeRoot.clicked.connect(self.handle_shp_root_browse)
        self.BrowseForOutputDir.clicked.connect(self.handle_output_dir_browse)

        self.all_files = 0
        self.total_files = 0
        self.files_left = 0
        self.files_processed = 0

    def handle_tab1_clear_button(self):
        """
        Handles the clear button clicked event
        """

        self.ImageRootInputEdit.clear()
        self.ShapeRootInputEdit.clear()
        self.OutputDirectoryEdit.clear()
        self.OutputWindow.clear()
        self.process_button_enabler()
        self.ProcessButton.setText("Process")

    def handle_tab2_clear_button(self):
        pass

    def handle_tab1_process_button(self):
        """
        Handles the process button clicked event
        """

        # Get parameters from GUI
        image_extension = self.ImageTypeCombo.currentText()
        image_path = self.ImageRootInputEdit.text()
        shp_path = self.ShapeRootInputEdit.text()
        working_directory = self.OutputDirectoryEdit.text()

        payload = (image_path, shp_path, working_directory, image_extension)

        self.ProcessButton.setText("Processing")
        self.ProcessButton.setDisabled(True)
        if len(self.ImageRootInputEdit.text()) > 0 and len(self.ShapeRootInputEdit.text()) > 0 \
                and len(self.OutputDirectoryEdit.text()) > 0:
            self.main(payload)

    def handle_img_root_browse(self):
        """
        Handles user clicking browse for image root path
        """

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ImageRootInputEdit.setText(openfile)

        if openfile:
            self.image_root_set = True
            self.process_button_enabler()

    def handle_shp_root_browse(self):
        """
        Handles user clicking browse for shp root path
        """
        self.shp_root_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.ShapeRootInputEdit.setText(openfile)

        if openfile:
            self.shp_root_set = True
            self.process_button_enabler()

    def handle_output_dir_browse(self):
        """
        Handles user clicking browse for output dir
        """
        self.working_directory_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.OutputDirectoryEdit.setText(openfile)

        if openfile:
            self.working_directory_set = True
            self.process_button_enabler()

    def process_button_enabler(self):
        """
        Checks if all three input text items are set and enabled process button if so
        """

        if self.ImageRootInputEdit.text() and self.ShapeRootInputEdit.text() and \
                self.OutputDirectoryEdit.text():
            self.ProcessButton.setEnabled(True)
            self.ProcessButton.setText("Process")

    def done(self):
        """
        Updates the output window when finished.
        """
        self.ProcessButton.setEnabled(True)
        app.processEvents()

    def create_new_filenames(self, paths, destination, image_extension):
        """
        rename image and shape files
        :param paths: tuple. first is image path, second is shp path
        :return: Tuple (orig path, new path, id)
        """

        image_ids = []
        index_counter = 0
        step = None
        extensions_to_search = None

        shp_extensions = ('.shp', '.dbf', '.shx', '.prj')

        if exists(destination):  # only run if the destination exists

            for path in paths:  # for image and shape path...

                files = []

                if index_counter == 0:  # image files
                    step = "imagery"
                    if image_extension == '.img':
                        extra_extensions = '.ige', '.rrd', '.rde'
                        extensions_to_search = [image_extension, '.ige', '.rrd', '.rde']
                    else:
                        extensions_to_search = image_extension

                if index_counter == 1:  # shapefiles
                    step = 'shape data'
                    extensions_to_search = shp_extensions

                    destination = join(destination, 'shp')  # set shp dest path

                print("\n* Parsing {}...".format(step))

                for (dirpath, dirnames, filenames) in walk(path):  # for each path in path tuple...
                    if "output" not in dirpath:
                        for file in filenames:  # and for each file found...
                            sid = None  # sid is the ID value that the file will be named
                            image_type = None  # pan or psh
                            type_destination = None  # destination path depending on image_type
                            extension = splitext(file)[1]

                            # Split old filename to recreate new filename.
                            if extension in extensions_to_search:  # don't process extra files
                                if extension in extra_extensions:
                                    print("Found extra file {}".format(file))
                                    logging.info("Found extra file {}".format(file))

                                original_file_path = join(dirpath, file)
                                file = file.replace('-', '_')  # replace hyphens with underscore
                                file = file.replace('.', '_')  # replace periods with underscore
                                file = file.split('_')  # split at underscores to create list

                                if index_counter == 0:  # Imagery step
                                    sid = file[0]

                                    if "PAN" in file or "pan" in file:
                                        image_type = 'PAN'
                                        type_destination = join(destination, 'PAN')  # set shp dest path

                                    elif 'PSH' in file or 'psh' in file:
                                        image_type = 'PSH'
                                        type_destination = join(destination, 'PSH')  # set shp dest path

                                    else:
                                        image_type = 'Uncategorized'
                                        type_destination = "uncategorized_images"
                                        text = "- WARNING: Could not categorize image {}" \
                                            .format(original_file_path)
                                        logging.warning(text)

                                    image_info = (file[0], image_type)
                                    image_ids.append(image_info)

                                if index_counter == 1:  # shape
                                    image_ids = tuple(image_ids)  # we don't need this as an array now
                                    if 'PIXEL' in file or 'pixel' in file:  # only want the PIXEL_SHAPE files
                                        sid, type = match_shp_to_image(file, image_ids)

                                if sid:
                                    # Sort images based on pan or psh
                                    if image_type in ["PSH", "PAN"]:
                                        new_filename = join(type_destination, "{0}_{1}{2}"
                                                            .format(sid,
                                                                    image_type,
                                                                    splitext(original_file_path)[1]))

                                    # Don't rename - just copy. Will have to manually modify name to
                                    # be sure it's accurate.
                                    elif image_type == 'Uncategorized':
                                        new_filename = join(type_destination, "{0}".format(file))

                                    else:
                                        new_filename = join(destination, "{0}_{1}{2}"
                                                            .format(sid, type,
                                                                    splitext(original_file_path)[1]))

                                    file = (original_file_path, new_filename, sid, image_type)
                                    files.append(file)

                                else:
                                    if splitext(original_file_path)[1] == '.shp':
                                        text = ("- ERROR: could not match image with "
                                                "filename {}"
                                                .format(original_file_path))
                                        logging.error(text)

                                self.files_processed += 1

                text = "\t - Copying {}".format(step)

                if len(files) > 0:
                    # Filter duplicate output files
                    # seen = set()
                    # out = []

                    # for a,b,c,d in files:
                    #    if b not in seen:
                    #        out.append((a,b,c,d))
                    #        seen.add(b)

                    # files = out

                    file_copier(files, destination)  # copy the files

                index_counter += 1  # increment the counter to begin copying shp

        else:
            text = ("- WARNING: destination directory {} does not exist and I "
                    "couldn't create it for you. "
                    "Did you enter a valid path?".format(destination))

            logging.warning(text)

    def main(self, payload):
        """
        Runs the entire thing
        :return:
        """

        self.ProcessButton.setDisabled(True)

        image_path = payload[0]
        shp_path = payload[1]
        working_directory = payload[2]
        image_extension = payload[3]

        text = "--Process began at {} --".format(get_datetime())

        # set up logfile
        logfile = join(working_directory, 'renamer.log')
        text = "\n* Setting up logfile: {}".format(logfile)

        logging.basicConfig(filename=logfile,
                            level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%',
                            filemode="w")

        logging.info("- INFO: image path: {0}, shp path: {1}, working directory: "
                     "{2}".format(image_path, shp_path, working_directory))

        paths = (image_path, shp_path)

        # Create the directories relative to user's working directory
        directories = (working_directory, join(working_directory, 'PSH'),
                       join(working_directory, 'PAN'),
                       join(working_directory, 'uncategorized_images'),
                       join(working_directory, 'shp'))

        print("* Creating directories...")
        for directory in directories:
            directory_creator(directory)

        self.create_new_filenames(paths, working_directory, image_extension)

        logging.info("- INFO: Finished at {})".format(get_datetime()))
        text = "\n-- Image/Shp processing complete at {} --".format(get_datetime())

        self.ProcessButton.setEnabled(True)
        self.ProcessButton.setText("Process")

        print("\n** Finished at {} **".format(get_datetime()))


def match_shp_to_image(shp_filename_values, image_ids):
    """
    Finds shapefiles that match image files, by name
    :param shp_filename_values: array containing split strings in shp filename
    :param image_ids: tuple of image names
    :return: matched id (string)
    """

    sid = None
    type = None

    for image_id in image_ids:
        if 'PIXEL' in shp_filename_values:
            for value in shp_filename_values:
                if value.isdigit() and len(value) == 12:
                    if value == image_id[0]:
                        sid = value  # try to match shp id to image id
                        type = image_id[1]
    return sid, type


def create_manifest(destination, data):
    """
    Create list of input/output files
    """

    file = join(destination, 'manifest.txt')

    time = get_datetime()

    with open(file, "a") as manifest_file:
        manifest_file.write('- {0}: copied from {1} written to {2}\n'.format(time, data[1], data[0]))


def get_checksum(file):
    """
    Returns sha1 checksum of file
    :param file: file
    :return: string (checksum)
    """
    # sha1_checksum = sha1()
    buffer_size = 256

    with open(file, 'rb') as f:
        while True:
            data = f.read(buffer_size)
            return sha1(data).hexdigest()


def file_copier(data, destination):
    """
    Copies files from source to destination
    :param data: tuple containing source, destination, ID and image type
    :return: IO
    """
    copied_count = 0

    if exists(destination):
        for file in data:  # copy each file

            if not exists(file[1]):

                original_file = file[0]
                new_file = file[1]

                original_checksum = get_checksum(original_file)
                copyfile(original_file, new_file)

                # Ensure output file is identical to input file
                while original_checksum != get_checksum(new_file):
                    logging.warning("File checksum mismatch. Attempting copy again. {}"
                                    .format(new_file))
                    copyfile(original_file, new_file)

                logging.info("- INFO: Copied file {0} to {1}".format(original_file, new_file))

                create_manifest(destination, (new_file, original_file))
                copied_count += 1
                print(" - Copied file {0} of {1}".format(copied_count, len(data)))

            else:
                text = ("- Warning: File {} already exists in destination. "
                        "Not copying.".format(file[1]))
                # print("\t".format(text))
                logging.warning(text)
    else:
        text = ("- WARNING: directory {} does not exist and I could "
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


class DatabaseIo:
    """
    Methods for storing and reading from spatialite db. Populating a spatialite db will allow for
    much faster processing if there are multiple iterations.
    """

    def __init__(self):
        """
        Initialize the class
        """

        # Set the DB path
        self.db_path = None
        self.get_db_path()

    def get_db_path(self):
        """
         Set path for spatialite db storage
        """

        if getattr(sys, 'frozen', False):  # Determine if running from an executable
            application_path = path.join(sys.path[0], "str.db")  # Get exe location
        else:
            application_path = path.dirname(__file__)  # if not exe, just use python script loc

        self.db_path = path.join(application_path, 'STR.db')

    def init_db(self):
        """
        Create .db file
        """


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

        pass

    def shapefile_bounds(self):
        """
        Gets the shapefile bounds (actual, not bb)
        """

        pass

    def shapefile_centroid(self):
        """
        Gets the shapefile centroid

        """

        pass


class ImageReader:
    """
    Contains methods for reading imagery for processing
    """

    def __init__(self, image_path):
        """
        Initialize the class
        """
        self.image_path = image_path

    def read_image(self):
        """
        Read the geotiff using GDAL
        """

        pass

    def image_bounds(self):
        """
        Get the geotiff bounding box
        """

        pass

    def image_centroid(self):
        """
        Gets the image centroid
        """

        pass


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


if __name__ == '__main__':
    app = QtWidgets.QApplication(argv)
    window = GUI()
    window.show()
    exit(app.exec_())
