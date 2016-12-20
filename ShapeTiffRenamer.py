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
import datetime
import gdal
import ogr
import ntpath
from shapely.geometry import Polygon, Point  # For centroid calculation
from shapely.ops import transform

# TODO: Incorporate gdaladdo to build pyramids

TEST = False


class GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):

        super(GUI, self).__init__()

        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setFixedSize(800, 180)  # no resizing
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

        self.BrowseForImageDir.clicked.connect(self.handle_img_root_browse)
        self.BrowseForOutputDir.clicked.connect(self.handle_output_dir_browse)
        self.BrowseForDb.clicked.connect(self.handle_browse_for_db)

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
            runner(payload)

    def handle_img_root_browse(self):
        """
        Handles user clicking browse for image root path
        """

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)

        try:
            self.ImageRootInputEdit.setText(openfile)
        except AttributeError as e:
            print("No image directory selected")

        if openfile:
            self.image_root_set = True
            self.process_button_enabler()

    def handle_shp_root_browse(self):
        """
        Handles user clicking browse for shp root path
        """

        self.shp_root_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)

        try:
            self.ShapeRootInputEdit.setText(openfile)
        except AttributeError as e:
            print("No shape directory selected")

        if openfile:
            self.shp_root_set = True
            self.process_button_enabler()

    def handle_output_dir_browse(self):
        """
        Handles user clicking browse for output dir
        """

        self.working_directory_set = False

        openfile = QtWidgets.QFileDialog.getExistingDirectory(self)

        try:
            self.OutputDirectoryEdit.setText(openfile)
        except AttributeError:
            print("No Image output dir selected")

        if openfile:
            self.working_directory_set = True
            self.process_button_enabler()

    def handle_browse_for_db(self):
        """Handles user clicking db browse button"""

        self.db_path_set = False

        openfile = QtWidgets.QFileDialog.getOpenFileName(self)

        try:
            self.OutputDirectoryEdit_2.setText(openfile)
        except AttributeError:
            print("No DB path selected.")

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

        if exists(destination):
            if image_extension == '.img':
                extensions_to_search.append(".ige")
                extensions_to_search.append(".rrd")

            # List of tuples that contain (image_filename, shape_filename)

            # Generate list of filepaths to imagery and shapedata
            print("* Creating file lists...")
            for (dirpath, dirnames, filenames) in walk(paths[0]):
                for file in filenames:
                    if splitext(file)[1] == image_extension:  # Only catch image files
                        image_paths.append(join(dirpath, file))

            for (dirpath, dirnames, filenames) in walk(paths[1]):
                for file in filenames:
                    if splitext(file)[1] == '.shp' and 'PIXEL' in file:  # OGR opens .shp extension
                        shape_paths.append(join(dirpath, file))

            print("* Testing shapes and rasters for spatial correlation...")
            image_paths = set(image_paths)  # For speed
            shape_paths = set(shape_paths)

            match = []
            for image in image_paths:
                best_distance = None
                best_match = None

                for shape in shape_paths:
                    # Run the actual intersection
                    _, feature_centroid, layer_centroid = intersect_shape_and_tif(image, shape)

                    current_distance, shape_cent, image_cent = distance_between_centroids(feature_centroid,
                                                                                          layer_centroid)

                    # get the closest match
                    if best_distance:
                        if current_distance < best_distance:
                            best_distance = current_distance
                            best_match = shape
                    else:
                        best_distance = current_distance
                        best_match = shape

                # dict of lists
                matched_files[image] = best_match

            # input(matched_files)
            # Now, move on to parsing filenames
            print("\n* Parsing files...")
            for image, shapefile in matched_files.items():
                list_index_counter = 0

                # Parse the imagery filenames
                image_path = image
                image_file = ntpath.basename(image_path)
                image_extension = splitext(image_path)[1]
                image_filename_list = listify_filename(image_file)
                image_sid = image_filename_list[0]

                if "PAN" in image_filename_list:
                    image_type = 'PAN'
                    image_type_destination = join(destination, 'PAN')  # set shp dest path

                    new_image_filename = join(image_type_destination, "{0}_{1}{2}"
                                              .format(image_sid,
                                                      image_type,
                                                      splitext(image)[1]))

                elif 'PSH' in image_filename_list:
                    image_type = 'PSH'
                    image_type_destination = join(destination, 'PSH')  # set shp dest path

                    new_image_filename = join(image_type_destination, "{0}_{1}{2}"
                                              .format(image_sid,
                                                      image_type,
                                                      splitext(image)[1]))

                else:
                    image_type = 'Uncategorized'
                    image_type_destination = None
                    text = "- WARNING: Could not categorize image {}" \
                        .format(image)
                    logging.warning(text)
                    print(text)

                    # Don't rename - just copy. Will have to manually modify name to
                    # be sure it's accurate.
                    new_filename = image_file

                # Parse the fhape filenames
                shape_path = shapefile
                shape_file = ntpath.basename(shape_path)
                shape_name = ntpath.basename(shape_path)[0]
                shape_extension = splitext(shape_path)[1]
                shape_filename_list = listify_filename(shape_file)

                files_to_copy = (image_path, new_image_filename, shape_path, image_sid)
                copier_payload.append(files_to_copy)

            text = "\t - Copying {}".format(step)

            if len(copier_payload) > 0:
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

    if not TEST:
        gui.ProcessButton.setDisabled(True)

        image_path = payload[0]
        shp_path = payload[1]
        working_directory = payload[2]
        image_extension = payload[3]

    else:
        image_path = "E:\\scriptTest\\input\\image"
        shp_path = "E:\\scriptTest\\GIS_FILES"
        working_directory = "E:\\scriptTest\\output"
        image_extension = ".img"

    # set up logfile
    logfile = join(working_directory, 'renamer.log')

    logging.basicConfig(filename=logfile,
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
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

    gui.create_new_filenames(paths, working_directory, image_extension)

    logging.info("- INFO: Finished at {})".format(get_datetime()))
    text = "\n-- Image/Shp processing complete at {} --".format(get_datetime())

    if not TEST:
        gui.ProcessButton.setEnabled(True)
        gui.ProcessButton.setText("Process")

    print("\n** Finished at {} **".format(get_datetime()))


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
    :param data: list of tuples containing (image_path, new_image_filename, shape_path, shape_name)
    :return: IO
    """
    shapefile_count = 0
    image_count = 0

    if exists(destination):
        for item in data:  # copy each file

            image_path = item[0]
            image_destination = item[1]
            shpdir = dirname(realpath(item[2]))
            _shape_output_name = item[3]

            # Build name for shape data
            shapefile_to_copy = []
            shape_name = (ntpath.basename(item[2]))
            shp_extensions = ('.shp', '.dbf', '.shx', '.prj')

            for extension in shp_extensions:
                # Build list of files to copy
                file = "{0}{1}".format(splitext(shape_name)[0], extension)
                to_copy = join(shpdir, file)
                shapefile_to_copy.append(to_copy)

                # Build new shapefile names and new paths
                shape_output_name = "{0}{1}".format(_shape_output_name, extension)
                new_shapefile_path = join(destination, "shp")
                new_shapefile_path = join(new_shapefile_path, shape_output_name)

                # Copy the shapefiles to the new shapefile path
                copyfile(to_copy, new_shapefile_path)

                logging.info("- INFO: Copied shapefile {0} to {1}"
                             .format(shapefile_to_copy, new_shapefile_path))

                create_manifest(destination, (item[2], new_shapefile_path))
                shapefile_count += 1

                print(" - Copied shapefile {0} of {1}".format(shapefile_count, len(data) * 4))

            if not exists(image_destination):

                copyfile(image_path, image_destination)
                logging.info("- INFO: Copied file {0} to {1}".format(image_path, image_destination))

                create_manifest(destination, (image_path, image_destination))
                image_count += 1
                print(" - Copied file {0} of {1}".format(image_count, len(data)))

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

        # Define the variables
        self.engine = None
        self.DBSession = None
        self.session = None
        self.metadata = None
        self.db_path = None

        # Initialize DB
        self.get_db_path()

    def get_db_path(self):
        """
         Set path for spatialite db storage
        """

        if getattr(sys, 'frozen', False):  # Determine if running from an executable
            application_path = join(sys.path[0], "str.db")  # Get exe location
        else:
            application_path = dirname(__file__)  # if not exe, just use python script loc

        self.db_path = path.join(application_path, 'STR.db')

        return self.db_path

    def init_db(self):
        """
        Create .db file
        """

        pass

        # Create the session
        # self.engine = create_engine('sqlite:///{}'.format(self.db_path))
        # self.metadata = MetaData(self.engine)
        # self.DBSession = sessionmaker(bind=self.engine)
        # self.session = self.DBSession()
        # self.metadata.create_all()  # Create the db

    def write_to_db(self):
        """
        Writes data to the database
        """

        pass


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
        # input("Pixel width: {}".format(self.pixelWidth))
        # input("Pixel height: {}".format(self.pixelHeight))

        # input("{0}: {1},{2}".format(self.image_path, self.x_right, self.y_bottom))
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


def distance_between_centroids(shape_path, image_path):
    """
    Checks the distance between two polygon objects using Shapely
    :param object_a: Shapely Polygon object
    :param object_b: Shapely Polygon Object
    :return: distance
    """

    # Temporarily reproject to get results in meters

    projection = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:4326'),
        pyproj.Proj(init='epsg:32639')

    )

    # reprojected_shape = transform(projection, shape_path)
    # reprojected_image = transform(projection, image_path)
    reprojected_image = image_path
    reprojected_shape = shape_path

    return reprojected_shape.distance(reprojected_image), reprojected_shape, reprojected_image


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

    db_io = DatabaseIo()
    db_io.init_db()  # Set up the DB

    # Start GUI
    app = QtWidgets.QApplication(argv)
    window = GUI()
    if not TEST:
        window.show()
        exit(app.exec_())

    else:
        runner(None)


if __name__ == '__main__':
    from models import SpatialiteDb

    if TEST:
        print("*** TESTING MODE. REMOVE TEST FLAG ***")
        app = None

    main()
