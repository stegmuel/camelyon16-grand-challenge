from concurrent.futures import ThreadPoolExecutor
import multiresolutionimageinterface as mir
from glob import glob
import os


def get_tumor_mask(save_dir, xml_queries, image_queries):
    """
    Computes the .tif masks from the .xml annotations.
    :param save_dir: location where to save the generated masks.
    :param xml_queries: location where to get the .xml annotations.
    :param image_queries: location where to get the original .tif WSIs.
    :return: None.
    """
    # Sample all the .xml files
    xml_filepaths = [f for query in xml_queries for f in glob(query)]

    # Sample all the .tif files
    image_filepaths = [f for query in image_queries for f in glob(query)]

    # Filter out files without match
    xml_filenames = set([f.split('/')[-1].split('.')[0] for f in xml_filepaths])
    image_filenames = set([f.split('/')[-1].split('.')[0] for f in image_filepaths])
    xml_filepaths = sorted([f for f in xml_filepaths if f.split('/')[-1].split('.')[0] in image_filenames],
                           key=lambda f: f.split('/')[-1].split('.')[0])
    image_filepaths = sorted([f for f in image_filepaths if f.split('/')[-1].split('.')[0] in xml_filenames],
                             key=lambda f: f.split('/')[-1].split('.')[0])

    # Create the output filepaths
    output_filepaths = sorted([os.path.join(save_dir, f.split('/')[-1].split('.')[0] + '.tif') for f in xml_filepaths],
                              key=lambda f: f.split('/')[-1].split('.')[0])

    # Display status
    print('Found {} matched .xml files'.format(len(output_filepaths)))

    # Initialize the image reader
    image_reader = mir.MultiResolutionImageReader()

    # Create the arguments
    args = [(image_reader, f_x, f_i, f_o) for f_x, f_i, f_o in zip(xml_filepaths, image_filepaths,
                                                                   output_filepaths)][120:]

    # Extract all trois from the slide
    with ThreadPoolExecutor() as executor:
        executor.map(compute_single_slide_mask, *zip(*args))


def compute_single_slide_mask(image_reader, f_x, f_i, f_o):
    # Display status
    slide_name = f_x.split('/')[-1].split('.')[0]
    print('Processsing slide {}.'.format(slide_name))

    # Read the input image
    input_image = image_reader.open(f_i)

    # Get the annotations
    annotation_list = mir.AnnotationList()
    xml_repository = mir.XmlRepository(annotation_list)
    xml_repository.setSource(f_x)
    xml_repository.load()
    annotation_mask = mir.AnnotationToMask()
    camelyon17_type_mask = False
    label_map = {'metastases': 1, 'normal': 2} if camelyon17_type_mask else {'_0': 1, '_1': 1, '_2': 0}
    conversion_order = ['metastases', 'normal'] if camelyon17_type_mask else ['_0', '_1', '_2']

    # Get the mask
    annotation_mask.convert(annotation_list, f_o, input_image.getDimensions(), input_image.getSpacing(), label_map,
                            conversion_order)


if __name__ == '__main__':
    save_dir = '/hdd/data/CAMELYON-16/tif_masks/'
    xml_queries = ['/hdd/data/CAMELYON-16/training/lesion_annotations/*.xml',
                   '/hdd/data/CAMELYON-16/testing/lesion_annotations/*.xml']
    image_queries = ['/hdd/data/CAMELYON-16/training/tumor/*.tif',
                     '/hdd/data/CAMELYON-16/testing/images/*tif']
    get_tumor_mask(save_dir=save_dir, xml_queries=xml_queries, image_queries=image_queries)
