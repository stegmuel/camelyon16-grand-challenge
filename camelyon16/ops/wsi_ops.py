import sys
from random import sample
from PIL import Image

from openslide import OpenSlide, OpenSlideUnsupportedFormatError
import matplotlib.pyplot as plt
from einops import rearrange
import numpy as np
import cv2

import camelyon16.utils as utils


class PatchExtractor(object):
    @staticmethod
    def extract_positive_patches_from_tumor_region(wsi_image, tumor_gt_mask, level_used,
                                                   bounding_boxes, patch_save_dir, patch_prefix,
                                                   patch_index, wsi_mask):
        """

            Extract positive patches targeting annotated tumor region

            Save extracted patches to desk as .png image files

            :param wsi_image:
            :param tumor_gt_mask:
            :param level_used:
            :param bounding_boxes: list of bounding boxes corresponds to tumor regions
            :param patch_save_dir: directory to save patches into
            :param patch_prefix: prefix for patch name
            :param patch_index:
            :return:
        """

        mag_factor = pow(2, level_used)
        tumor_gt_mask = cv2.cvtColor(tumor_gt_mask, cv2.COLOR_BGR2GRAY)
        plt.imshow(tumor_gt_mask)
        plt.show()
        print('No. of ROIs to extract patches from: %d' % len(bounding_boxes))
        slide_filename = wsi_image._filename.split('/')[-1].split('.')[0]

        for bounding_box in bounding_boxes:
            try:
                b_x_start = int(bounding_box[0])
                b_y_start = int(bounding_box[1])
                b_x_end = int(bounding_box[0]) + int(bounding_box[2])
                b_y_end = int(bounding_box[1]) + int(bounding_box[3])

                width = int(bounding_box[2]) * mag_factor
                height = int(bounding_box[3]) * mag_factor
                print('Dimension of the bounding box: {} x {}'.format(height, width))
                xs = np.arange(start=int(b_x_start * mag_factor), stop=int(b_x_end * mag_factor),
                               step=utils.PATCH_SIZE_W)
                ys = np.arange(start=int(b_y_start * mag_factor), stop=int(b_y_end * mag_factor),
                               step=utils.PATCH_SIZE_H)
                xv, yv = np.meshgrid(xs, ys)
                xv_yv = np.stack([xv, yv])
                xv_yv = list(map(lambda x: tuple(x), list(rearrange(xv_yv, 'd h w -> (h w) d'))))
                patch_dim_h = int(utils.PATCH_SIZE_H / mag_factor)
                patch_dim_w = int(utils.PATCH_SIZE_W / mag_factor)

                # Filer the non-tumor patches
                corners = [(int(x / mag_factor), int(y / mag_factor)) for x, y in xv_yv]
                xv_yv = [(x, y) for (x, y), (x_c, y_c) in zip(xv_yv, corners)
                         if np.mean(tumor_gt_mask[y_c: y_c + patch_dim_h, x_c: x_c + patch_dim_w]) > utils.PIXEL_BLACK]
                print('Kept {} patches out of {}.'.format(len(xv_yv), len(corners)))

                for x, y in xv_yv:
                    # Read the image
                    patch = wsi_image.read_region((x, y), utils.LEVEL, (utils.PATCH_SIZE_W, utils.PATCH_SIZE_H))
                    patch = patch.convert('RGB')

                    # Save the patch
                    patch_name = '_'.join([slide_filename, str(x), str(y)]) + '.jpg'
                    patch.save(patch_save_dir + patch_name, 'JPEG')
                    patch_index += 1
                    patch.close()

                    # Read the corresponding mask
                    patch_mask = wsi_mask.read_region((x, y), utils.LEVEL, (utils.PATCH_SIZE_W, utils.PATCH_SIZE_H))
                    patch_mask = patch_mask.convert('RGB')
                    patch_mask = Image.fromarray(255 * np.array(patch_mask))

                    # Save the patch
                    patch_mask_name = '_'.join([slide_filename, str(x), str(y)]) + '_mask.jpg'
                    patch_mask.save(patch_save_dir + patch_mask_name, 'JPEG')
                    patch_mask.close()
            except IndexError:
                continue
        return patch_index

    @staticmethod
    def extract_negative_patches_from_normal_wsi(wsi_image, image_open, level_used,
                                                 bounding_boxes, patch_save_dir, patch_prefix,
                                                 patch_index):
        """
            Extract negative patches from Normal WSIs

            Save extracted patches to desk as .png image files

            :param wsi_image:
            :param image_open:
            :param level_used:
            :param bounding_boxes: list of bounding boxes corresponds to detected ROIs
            :param patch_save_dir: directory to save patches into
            :param patch_prefix: prefix for patch name
            :param patch_index:
            :return:

        """

        mag_factor = pow(2, level_used)

        print('No. of ROIs to extract patches from: %d' % len(bounding_boxes))
        slide_filename = wsi_image._filename.split('/')[-1].split('.')[0]

        for bounding_box in bounding_boxes:
            b_x_start = int(bounding_box[0])
            b_y_start = int(bounding_box[1])
            b_x_end = int(bounding_box[0]) + int(bounding_box[2])
            b_y_end = int(bounding_box[1]) + int(bounding_box[3])

            width = int(bounding_box[2]) * mag_factor
            height = int(bounding_box[3]) * mag_factor
            print('Dimension of the bounding box: {} x {}'.format(height, width))
            xs = np.arange(start=int(b_x_start * mag_factor), stop=int(b_x_end * mag_factor), step=utils.PATCH_SIZE_W)
            ys = np.arange(start=int(b_y_start * mag_factor), stop=int(b_y_end * mag_factor), step=utils.PATCH_SIZE_H)
            xv, yv = np.meshgrid(xs, ys)
            xv_yv = np.stack([xv, yv])
            xv_yv = list(map(lambda x: tuple(x), list(rearrange(xv_yv, 'd h w -> (h w) d'))))

            # Filer the non-tumor patches
            centers = [(int((x + utils.PATCH_SIZE_W / 2) / mag_factor), int((y + utils.PATCH_SIZE_H / 2) / mag_factor))
                       for x, y in xv_yv]
            xv_yv = [(x, y) for (x, y), (x_c, y_c) in zip(xv_yv, centers)
                     if int(image_open[y_c, x_c]) is not utils.PIXEL_BLACK]
            if len(xv_yv) > utils.NUM_NEGATIVE_PATCHES_FROM_EACH_BBOX:
                xv_yv = sample(xv_yv, utils.NUM_NEGATIVE_PATCHES_FROM_EACH_BBOX)
            print('Kept {} patches out of {}.'.format(len(xv_yv), len(centers)))

            for x, y in xv_yv:
                patch = wsi_image.read_region((x, y), utils.LEVEL, (utils.PATCH_SIZE_W, utils.PATCH_SIZE_H))

                # Save the patch
                patch_name = '_'.join([slide_filename, str(x), str(y)]) + '.jpg'
                patch = patch.convert('RGB')
                patch.save(patch_save_dir + patch_name, 'JPEG')
                patch_index += 1
                patch.close()

        return patch_index

    @staticmethod
    def extract_negative_patches_from_tumor_wsi(wsi_image, tumor_gt_mask, image_open, level_used,
                                                bounding_boxes, patch_save_dir, patch_prefix,
                                                patch_index):
        """
            From Tumor WSIs extract negative patches from Normal area (reject tumor area)
            Save extracted patches to desk as .png image files

            :param wsi_image:
            :param tumor_gt_mask:
            :param image_open: morphological open image of wsi_image
            :param level_used:
            :param bounding_boxes: list of bounding boxes corresponds to tumor regions
            :param patch_save_dir: directory to save patches into
            :param patch_prefix: prefix for patch name
            :param patch_index:
            :return:

        """
        mag_factor = pow(2, level_used)
        tumor_gt_mask = cv2.cvtColor(tumor_gt_mask, cv2.COLOR_BGR2GRAY)
        print('No. of ROIs to extract patches from: %d' % len(bounding_boxes))
        slide_filename = wsi_image._filename.split('/')[-1].split('.')[0]

        for bounding_box in bounding_boxes:
            try:
                b_x_start = int(bounding_box[0])
                b_y_start = int(bounding_box[1])
                b_x_end = int(bounding_box[0]) + int(bounding_box[2])
                b_y_end = int(bounding_box[1]) + int(bounding_box[3])

                width = int(bounding_box[2]) * mag_factor
                height = int(bounding_box[3]) * mag_factor
                print('Dimension of the bounding box: {} x {}'.format(height, width))
                xs = np.arange(start=int(b_x_start * mag_factor), stop=int(b_x_end * mag_factor), step=utils.PATCH_SIZE_W)
                ys = np.arange(start=int(b_y_start * mag_factor), stop=int(b_y_end * mag_factor), step=utils.PATCH_SIZE_W)
                xv, yv = np.meshgrid(xs, ys)
                xv_yv = np.stack([xv, yv])
                xv_yv = list(map(lambda x: tuple(x), list(rearrange(xv_yv, 'd h w -> (h w) d'))))

                # Filer the non-tumor patches
                centers = [(int((x + utils.PATCH_SIZE_W / 2) / mag_factor), int((y + utils.PATCH_SIZE_H / 2) / mag_factor))
                           for x, y in xv_yv]
                corners = [(int(x / mag_factor), int(y / mag_factor)) for x, y in xv_yv]
                patch_dim_h = int(utils.PATCH_SIZE_H / mag_factor)
                patch_dim_w = int(utils.PATCH_SIZE_W / mag_factor)

                # Filter background patches
                xv_yv = [(x, y) for (x, y), (x_c, y_c) in zip(xv_yv, centers) if
                         int(image_open[y_c, x_c]) is not utils.PIXEL_BLACK]

                xv_yv = [(x, y) for (x, y), (x_c, y_c) in zip(xv_yv, corners) if
                         np.mean(tumor_gt_mask[y_c: y_c + patch_dim_h, x_c: x_c + patch_dim_w]) == float(utils.PIXEL_BLACK)]
                if len(xv_yv) > utils.NUM_NEGATIVE_PATCHES_FROM_EACH_BBOX:
                    xv_yv = sample(xv_yv, utils.NUM_NEGATIVE_PATCHES_FROM_EACH_BBOX)
                print('Kept {} patches out of {}.'.format(len(xv_yv), len(centers)))

                for x, y in xv_yv:
                    patch = wsi_image.read_region((x, y), utils.LEVEL, (utils.PATCH_SIZE_W, utils.PATCH_SIZE_H))
                    patch = patch.convert('RGB')

                    # Save the patch
                    patch_name = '_'.join([slide_filename, str(x), str(y)]) + '.jpg'
                    patch.save(patch_save_dir + patch_name, 'JPEG')
                    patch_index += 1
                    patch.close()
            except IndexError:
                continue

        return patch_index

    @staticmethod
    def extract_patches_from_heatmap_false_region_tumor(wsi_image, wsi_mask, tumor_gt_mask, image_open,
                                                        heatmap_prob,
                                                        level_used, bounding_boxes,
                                                        patch_save_dir_pos, patch_save_dir_neg,
                                                        patch_prefix_pos, patch_prefix_neg,
                                                        patch_index):
        """

            From Tumor WSIs extract negative patches from Normal area (reject tumor area)
                        Save extracted patches to desk as .png image files

            :param wsi_image:
            :param wsi_mask:
            :param tumor_gt_mask:
            :param image_open: morphological open image of wsi_image
            :param heatmap_prob:
            :param level_used:
            :param bounding_boxes: list of bounding boxes corresponds to tumor regions
            :param patch_save_dir_pos: directory to save positive patches into
            :param patch_save_dir_neg: directory to save negative patches into
            :param patch_prefix_pos: prefix for positive patch name
            :param patch_prefix_neg: prefix for negative patch name
            :param patch_index:
            :return:
        """

        mag_factor = pow(2, level_used)
        tumor_gt_mask = cv2.cvtColor(tumor_gt_mask, cv2.COLOR_BGR2GRAY)
        print('No. of ROIs to extract patches from: %d' % len(bounding_boxes))

        for bounding_box in bounding_boxes:
            b_x_start = int(bounding_box[0])
            b_y_start = int(bounding_box[1])
            b_x_end = int(bounding_box[0]) + int(bounding_box[2])
            b_y_end = int(bounding_box[1]) + int(bounding_box[3])
            col_cords = np.arange(b_x_start, b_x_end)
            row_cords = np.arange(b_y_start, b_y_end)

            for row in row_cords:
                for col in col_cords:
                    if int(image_open[row, col]) is not utils.PIXEL_BLACK:  # consider pixels from ROI only
                        # extract patch corresponds to false positives
                        if heatmap_prob[row, col] >= utils.TUMOR_PROB_THRESHOLD:
                            if int(tumor_gt_mask[row, col]) == utils.PIXEL_BLACK:
                                # mask_gt does not contain tumor area
                                mask = wsi_mask.read_region((col * mag_factor, row * mag_factor), 0,
                                                            (utils.PATCH_SIZE, utils.PATCH_SIZE))
                                mask_gt = cv2.cvtColor(np.array(mask), cv2.COLOR_BGR2GRAY)
                                white_pixel_cnt_gt = cv2.countNonZero(mask_gt)
                                if white_pixel_cnt_gt == 0:
                                    patch = wsi_image.read_region((col * mag_factor, row * mag_factor), 0,
                                                                  (utils.PATCH_SIZE, utils.PATCH_SIZE))
                                    patch.save(patch_save_dir_neg + patch_prefix_neg + str(patch_index), 'PNG')
                                    patch_index += 1
                                    patch.close()

                                mask.close()
                        # extract patch corresponds to false negatives
                        elif int(tumor_gt_mask[row, col]) is not utils.PIXEL_BLACK \
                                and heatmap_prob[row, col] < utils.TUMOR_PROB_THRESHOLD:
                            # mask_gt does not contain tumor area
                            mask = wsi_mask.read_region((col * mag_factor, row * mag_factor), 0,
                                                        (utils.PATCH_SIZE, utils.PATCH_SIZE))
                            mask_gt = cv2.cvtColor(np.array(mask), cv2.COLOR_BGR2GRAY)
                            white_pixel_cnt_gt = cv2.countNonZero(mask_gt)
                            if white_pixel_cnt_gt >= ((utils.PATCH_SIZE * utils.PATCH_SIZE) * 0.85):
                                patch = wsi_image.read_region((col * mag_factor, row * mag_factor), 0,
                                                              (utils.PATCH_SIZE, utils.PATCH_SIZE))
                                patch.save(patch_save_dir_pos + patch_prefix_pos + str(patch_index), 'PNG')
                                patch_index += 1
                                patch.close()

                            mask.close()

        return patch_index

    @staticmethod
    def extract_patches_from_heatmap_false_region_normal(wsi_image, image_open,
                                                         heatmap_prob,
                                                         level_used, bounding_boxes,
                                                         patch_save_dir_neg,
                                                         patch_prefix_neg,
                                                         patch_index):
        """

            From Tumor WSIs extract negative patches from Normal area (reject tumor area)
                        Save extracted patches to desk as .png image files

            :param wsi_image:
            :param image_open: morphological open image of wsi_image
            :param heatmap_prob:
            :param level_used:
            :param bounding_boxes: list of bounding boxes corresponds to tumor regions
            :param patch_save_dir_neg: directory to save negative patches into
            :param patch_prefix_neg: prefix for negative patch name
            :param patch_index:
            :return:
        """

        mag_factor = pow(2, level_used)
        print('No. of ROIs to extract patches from: %d' % len(bounding_boxes))

        for bounding_box in bounding_boxes:
            b_x_start = int(bounding_box[0])
            b_y_start = int(bounding_box[1])
            b_x_end = int(bounding_box[0]) + int(bounding_box[2])
            b_y_end = int(bounding_box[1]) + int(bounding_box[3])
            col_cords = np.arange(b_x_start, b_x_end)
            row_cords = np.arange(b_y_start, b_y_end)

            for row in row_cords:
                for col in col_cords:
                    if int(image_open[row, col]) is not utils.PIXEL_BLACK:  # consider pixels from ROI only
                        # extract patch corresponds to false positives
                        if heatmap_prob[row, col] >= utils.TUMOR_PROB_THRESHOLD:
                            # mask_gt does not contain tumor area
                            patch = wsi_image.read_region((col * mag_factor, row * mag_factor), 0,
                                                          (utils.PATCH_SIZE, utils.PATCH_SIZE))
                            patch.save(patch_save_dir_neg + patch_prefix_neg + str(patch_index), 'PNG')
                            patch_index += 1
                            patch.close()

        return patch_index


class WSIOps(object):
    """
        # ================================
        # Class to annotate WSIs with ROIs
        # ================================

    """

    def_level = 7

    @staticmethod
    def read_wsi_mask(mask_path, level=def_level):
        try:
            wsi_mask = OpenSlide(mask_path)

            mask_image = np.array(wsi_mask.read_region((0, 0), level,
                                                       wsi_mask.level_dimensions[level]))

        except OpenSlideUnsupportedFormatError:
            print('Exception: OpenSlideUnsupportedFormatError')
            return None, None

        return wsi_mask, mask_image

    @staticmethod
    def read_wsi_normal(wsi_path):
        """
            # =====================================================================================
            # read WSI image and resize
            # Due to memory constraint, we use down sampled (4th level, 1/32 resolution) image
            # ======================================================================================
        """
        try:
            wsi_image = OpenSlide(wsi_path)
            level_used = wsi_image.level_count - 1
            rgb_image = np.array(wsi_image.read_region((0, 0), level_used,
                                                       wsi_image.level_dimensions[level_used]))

        except OpenSlideUnsupportedFormatError:
            print('Exception: OpenSlideUnsupportedFormatError')
            return None, None, None

        return wsi_image, rgb_image, level_used

    @staticmethod
    def read_wsi_tumor(wsi_path, mask_path):
        """
            # =====================================================================================
            # read WSI image and resize
            # Due to memory constraint, we use down sampled (4th level, 1/32 resolution) image
            # ======================================================================================
        """
        try:
            wsi_image = OpenSlide(wsi_path)
            wsi_mask = OpenSlide(mask_path)

            level_used = min(wsi_image.level_count - 1, 5)

            # test = np.asarray(wsi_mask.get_thumbnail((382, 864)))
            # print(test.shape)
            # plt.imshow(test[:, :, 0])
            # plt.show()
            rgb_image = np.array(wsi_image.read_region((0, 0), level_used,
                                                       wsi_image.level_dimensions[level_used]))

            mask_level = min(wsi_mask.level_count - 1, 5)
            tumor_gt_mask = wsi_mask.read_region((0, 0), mask_level,
                                                 wsi_image.level_dimensions[mask_level])
            resize_factor = float(1.0 / pow(2, level_used - mask_level))
            # print('resize_factor: %f' % resize_factor)
            tumor_gt_mask = cv2.resize(np.array(tumor_gt_mask), (0, 0), fx=resize_factor, fy=resize_factor)


            # wsi_mask.close()
        except OpenSlideUnsupportedFormatError:
            print('Exception: OpenSlideUnsupportedFormatError')
            return None, None, None, None

        return wsi_image, rgb_image, wsi_mask, tumor_gt_mask, level_used

    def find_roi_bbox_tumor_gt_mask(self, mask_image):
        mask = cv2.cvtColor(mask_image, cv2.COLOR_BGR2GRAY)
        bounding_boxes, _ = self.get_bbox(np.array(mask))
        return bounding_boxes

    def find_roi_bbox(self, rgb_image):
        # hsv -> 3 channel
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2HSV)
        lower_red = np.array([40, 40, 40])
        upper_red = np.array([200, 200, 200])
        # mask -> 1 channel
        mask = cv2.inRange(hsv, lower_red, upper_red)

        close_kernel = np.ones((20, 20), dtype=np.uint8)
        image_close = cv2.morphologyEx(np.array(mask), cv2.MORPH_CLOSE, close_kernel)
        open_kernel = np.ones((5, 5), dtype=np.uint8)
        image_open = cv2.morphologyEx(np.array(image_close), cv2.MORPH_OPEN, open_kernel)
        bounding_boxes, rgb_contour = self.get_bbox(image_open, rgb_image=rgb_image)
        return bounding_boxes, rgb_contour, image_open

    @staticmethod
    def get_image_open(wsi_path):
        try:
            wsi_image = OpenSlide(wsi_path)
            level_used = wsi_image.level_count - 1
            rgb_image = np.array(wsi_image.read_region((0, 0), level_used,
                                                       wsi_image.level_dimensions[level_used]))
            wsi_image.close()
        except OpenSlideUnsupportedFormatError:
            raise ValueError('Exception: OpenSlideUnsupportedFormatError for %s' % wsi_path)

        # hsv -> 3 channel
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2HSV)
        lower_red = np.array([20, 20, 20])
        upper_red = np.array([200, 200, 200])
        # mask -> 1 channel
        mask = cv2.inRange(hsv, lower_red, upper_red)

        close_kernel = np.ones((20, 20), dtype=np.uint8)
        image_close = cv2.morphologyEx(np.array(mask), cv2.MORPH_CLOSE, close_kernel)
        open_kernel = np.ones((5, 5), dtype=np.uint8)
        image_open = cv2.morphologyEx(np.array(image_close), cv2.MORPH_OPEN, open_kernel)

        return image_open

    @staticmethod
    def get_bbox(cont_img, rgb_image=None):
        # _, contours, _ = cv2.findContours(cont_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours, _ = cv2.findContours(cont_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rgb_contour = None
        if rgb_image is not None:
            rgb_contour = rgb_image.copy()
            line_color = (255, 0, 0)  # blue color code
            cv2.drawContours(rgb_contour, contours, -1, line_color, 2)
        bounding_boxes = [cv2.boundingRect(c) for c in contours]
        return bounding_boxes, rgb_contour

    @staticmethod
    def draw_bbox(image, bounding_boxes):
        rgb_bbox = image.copy()
        for i, bounding_box in enumerate(bounding_boxes):
            x = int(bounding_box[0])
            y = int(bounding_box[1])
            cv2.rectangle(rgb_bbox, (x, y), (x + bounding_box[2], y + bounding_box[3]), color=(0, 0, 255),
                          thickness=2)
        return rgb_bbox

    @staticmethod
    def split_bbox(image, bounding_boxes, image_open):
        rgb_bbox_split = image.copy()
        for bounding_box in bounding_boxes:
            for x in range(bounding_box[0], bounding_box[0] + bounding_box[2]):
                for y in range(bounding_box[1], bounding_box[1] + bounding_box[3]):
                    if int(image_open[y, x]) == 1:
                        cv2.rectangle(rgb_bbox_split, (x, y), (x, y),
                                      color=(255, 0, 0), thickness=2)

        return rgb_bbox_split
