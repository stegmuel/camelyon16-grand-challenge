from camelyon16.ops.wsi_ops import PatchExtractor, WSIOps
from glob import glob
from camelyon16.preprocess.extract_patches import extract_positive_patches_from_tumor_wsi, \
    extract_negative_patches_from_tumor_wsi, extract_negative_patches_from_normal_wsi


if __name__ == '__main__':
    use_tumor_slides = False
    # Instantiate a wsi-ops object
    wsi_ops = WSIOps()

    # Instantiate a patch extractor
    patch_extractor = PatchExtractor()

    # Set the queries
    if use_tumor_slides:
        image_queries = ['/media/thomas/Samsung_T5/CAMELYON-16/training/tumor/*.tif']
        mask_queries = ['/media/thomas/Samsung_T5/CAMELYON-16/tif_masks/*.tif']

        image_paths = [filepath for query in image_queries for filepath in glob(query)]
        mask_paths = [filepath for query in mask_queries for filepath in glob(query)]

        # Match the names
        image_names = set([path.split('/')[-1].split('.')[0] for path in image_paths])
        mask_names = set([path.split('/')[-1].split('.')[0] for path in mask_paths])
        matched_names = image_names.intersection(mask_names)
        image_paths = [path for path in image_paths if path.split('/')[-1].split('.')[0] in matched_names]
        mask_paths = [path for path in mask_paths if path.split('/')[-1].split('.')[0] in matched_names]
        image_paths = sorted(image_paths, key=lambda p: p.split('/')[-1].split('.')[0])
        mask_paths = sorted(mask_paths, key=lambda p: p.split('/')[-1].split('.')[0])
    else:
        image_queries = ['/media/thomas/Samsung_T5/CAMELYON-16/training/normal/*.tif']
        image_paths = [filepath for query in image_queries for filepath in glob(query)]



    # Extract tumor patches
    if use_tumor_slides:
        extract_positive_patches_from_tumor_wsi(image_paths, mask_paths, wsi_ops, patch_extractor, 0)
        # extract_negative_patches_from_tumor_wsi(image_paths, mask_paths, wsi_ops, patch_extractor, 0)
    else:
        extract_negative_patches_from_normal_wsi(image_paths, wsi_ops, patch_extractor, 0)