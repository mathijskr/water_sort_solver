#!/usr/bin/env python3

import cv2
import sys
import numpy as np


filename = sys.argv[1]
visualize = len(sys.argv) > 2 and (sys.argv[2] == "-v" or sys.argv[2] == "--verbose" or sys.argv[2] == "--visualize")

image = cv2.imread(filename)
# Remove interface buttons
height = image.shape[0]
image_cropped = image[int(height * 0.15):height - int(height * 0.12), :] # empirically found

# Convert to graycsale
image_gray = cv2.cvtColor(image_cropped, cv2.COLOR_BGR2GRAY)

# Canny Edge Detection
image_edges = cv2.Canny(image=image_gray, threshold1=100, threshold2=200) # empirically found

# External to only detect the cylinders
contours, hierarchy = cv2.findContours(image=image_edges, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

contour_areas = map(cv2.contourArea, contours)
contour_area_threshold = max(contour_areas) * 0.95 # empirically found
cylinder_contours = list(filter(lambda c: cv2.contourArea(c) >= contour_area_threshold, contours))

image_with_cylinder_contours = image_cropped.copy()
cv2.drawContours(image=image_with_cylinder_contours, contours=cylinder_contours, contourIdx=-1, color=(0,255,0), thickness=2, lineType=cv2.LINE_AA)

# From https://medium.com/analytics-vidhya/tutorial-how-to-scale-and-rotate-contours-in-opencv-using-python-f48be59c35a2
def scale_contour(cnt, scale):
    (scale_x, scale_y) = scale
    M = cv2.moments(cnt)
    cx = int(M['m10']/M['m00'])
    cy = int(M['m01']/M['m00'])
    cnt_norm = cnt - [cx, cy]
    cnt_scaled = cnt_norm * [scale_x, scale_y] + [cx, cy]
    return cnt_scaled.astype(np.int32)

def translate_contour(cnt, translation):
    (translate_x, translate_y) = translation
    M = cv2.moments(cnt)
    cx = int(M['m10']/M['m00'])
    cy = int(M['m01']/M['m00'])
    cnt_norm = cnt - [cx, cy]
    cnt_translated = cnt_norm + [cx, cy] + [translate_x, translate_y]
    return cnt_translated.astype(np.int32)

# The sides of the cylinder are shaded. Extract only the middle, non-shaded, part.
cylinder_contours = map(lambda c: scale_contour(c, (0.2, 0.83)), cylinder_contours) # empirically found
cylinder_contours = list(map(lambda c: translate_contour(c, (0, 0.013 * height)), cylinder_contours)) # empirically found
# To visualize the detected contours and how they are scaled and translated to zoom in on the interesting parts:
image_with_scaled_contours = image_cropped.copy()
cv2.drawContours(image=image_with_scaled_contours, contours=cylinder_contours, contourIdx=-1, color=(0,255,0), thickness=2, lineType=cv2.LINE_AA)

cylinder_middle_lines = []
for c in cylinder_contours:
    # I don't understand this, but it works :)
    min_y_index = np.argmin(c[:, 0, 1])
    max_y_index = np.argmax(c[:, 0, 1])
    min_y = c[min_y_index][0][1]
    max_y = c[max_y_index][0][1]
    middle_x = round(np.mean(c, axis = 0)[0][0])
    cylinder_middle_lines.append(((middle_x, min_y), (middle_x, max_y)))

# To visualize the calculated middle lines of each cylinder:
image_with_middle_lines = image_cropped.copy()
for (begin, end) in cylinder_middle_lines:
    green = (0,255,0)
    cv2.line(image_with_middle_lines, begin, end, green, 3)


# Two colors are considered the same when they have the same hue value
image_cropped_hsv = cv2.cvtColor(image_cropped, cv2.COLOR_BGR2HSV)


hue_similarity_threshold = 4 # empirically found
saturation_simularity_threshold = 40 # empirically found
def hsv_similar_colors(color_a, color_b):
    (ha, sa, va) = color_a
    (hb, sb, vb) = color_b
    return abs(int(hb)-int(ha)) < hue_similarity_threshold and abs(int(sb)-int(sa)) < saturation_simularity_threshold


def find_similar_color(hsv_color, found_colors):
    for hsv_found_color in found_colors.keys():
        if hsv_similar_colors(hsv_color, hsv_found_color):
            return hsv_found_color

all_cylinder_colors = []
all_cylinder_heights = []
color_bar_minimum_height = 20 # empirically found
for ((x, min_y), (x, max_y)) in cylinder_middle_lines:
    current_color = None
    current_color_height = 0
    cylinder_colors = []

    cylinder_pixels = image_cropped_hsv[min_y:max_y,x,:]
    cylinder_pixels_rolled = np.roll(cylinder_pixels, 1, axis=0)
    # Compare against 1-shifted copy to detect color changes.
    cylinder_changes = cylinder_pixels_rolled - cylinder_pixels
    color_transition_ys = [y for (y, change) in enumerate(list(cylinder_changes)) if tuple(change) != (0, 0, 0)]
    # Only keep 1 coordinate of every transition.
    i = 0
    while i < len(color_transition_ys) - 1:
        if color_transition_ys[i+1] - color_transition_ys[i] <= color_bar_minimum_height:
            color_transition_ys.pop(i)
            continue
        i += 1
    color_transition_ys = min_y + np.array(color_transition_ys)
    transition_distances = (color_transition_ys - np.roll(color_transition_ys, 1))
    # Take the color right inbetween two transitions.
    color_ys = (color_transition_ys - transition_distances // 2)[1:]
    hsv_colors = image_cropped_hsv[color_ys,x,:]
    all_cylinder_colors.append(hsv_colors)
    all_cylinder_heights.append(transition_distances[1:])

one_color_height = min(map(min, all_cylinder_heights))

color_i = 0
colors_found = {}
all_cylinder_colors_labeled = []
for (cylinder, color_heights) in zip(all_cylinder_colors, all_cylinder_heights):
    cylinder_colors_labeled = []
    for (color, height) in zip(cylinder, color_heights):
       previously_encountered_color = find_similar_color(tuple(color), colors_found)
       if previously_encountered_color:
           color_label = colors_found[previously_encountered_color]
       else:
           color_label = color_i
           color_i += 1
           colors_found[tuple(color)] = color_label

       cylinder_colors_labeled += [color_label] * (height // one_color_height)

    all_cylinder_colors_labeled.append(cylinder_colors_labeled)


# # Print result
# # The cylinders are printed from top left to bottom right.
# # Each row represents a cylinder.
# # The colors are printed from top to bottom per cylinder.
color_labels = list(colors_found.values())
most_common_color = max(set(color_labels), key=color_labels.count) # Assume most common color is the empty space, since there are (always?) at least two empty cylinders.
for cylinder in reversed(all_cylinder_colors_labeled):
    for (i, color_index) in enumerate(cylinder):
        end = "\n" if i == len(cylinder) - 1 else " "
        label = "E" if color_index == most_common_color else color_index
        print(label, end=end)


if visualize:
    desired_width = 500
    desired_height = 400


    color_index_to_bgr = {i : cv2.cvtColor(np.uint8([[[hsv[0], hsv[1], hsv[2]]]]), cv2.COLOR_HSV2BGR)[0][0] for (hsv, i) in colors_found.items()}
    visualized_result = 255 * np.ones(shape=[desired_height, desired_width, 3], dtype = np.uint8)
    bar_width = desired_width // (2 * len(all_cylinder_colors_labeled))
    bar_height = desired_height // len(all_cylinder_colors_labeled[0])
    x = 0
    y = 0
    for cylinder in reversed(all_cylinder_colors_labeled):
        for color_index in cylinder:
            cv2.rectangle(visualized_result, pt1=(x,y), pt2=(x+bar_width,y+bar_height), color=tuple(map(int, color_index_to_bgr[color_index])), thickness=40)
            y += bar_height
        x += bar_width * 2
        y = 0


    images = (image_cropped, cv2.cvtColor(image_edges, cv2.COLOR_GRAY2BGR), image_with_cylinder_contours, image_with_scaled_contours, image_with_middle_lines, visualized_result)
    images = list(map(lambda img: cv2.resize(img, (desired_width, desired_height)), images))
    first_row = images[:3]
    second_row = images[3:]
    visualizations = np.vstack((np.hstack(tuple(first_row)), np.hstack(tuple(second_row))))
    cv2.imshow('Visualizations', visualizations)
    cv2.waitKey(0)
