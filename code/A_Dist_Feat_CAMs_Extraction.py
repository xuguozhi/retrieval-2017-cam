from scipy.misc import imread
import time
import sys
import h5py
import numpy as np
from cam_utils import extract_feat_cam, extract_feat_cam_all
from vgg_cam import VGGCAM
from utils import create_folders, save_data, preprocess_images, preprocess_query
from pooling_functions import weighted_cam_pooling


# Dataset Selection
dataset = 'distractors100k'

# Extract Online or offline
aggregation_type = 'Online'

# Image Pre-processing

# Horizontal Images
size_h = [1024, 720]
# Vertical Images
size_v = [720, 1024]

dim = '1024x720'

# Mean to substract
mean_data = 'Imagenet'

# Model Selection
model_name = 'Vgg_16_CAM'

if mean_data == 'Places':
    mean_value = [104, 166.66, 122.67]
    folder = 'places/'
elif mean_data == 'Imagenet':
    mean_value = [123.68, 116.779, 103.939]
    folder = 'imagenet/'
else:
    mean_value = [0, 0, 0]

# Model Selection: VGG_CAM
if model_name == 'Vgg_16_CAM':
    nb_classes = 1000
    VGGCAM_weight_path = '/imatge/ajimenez/work/ITR/models/vgg_cam_weights.h5'
    layer = 'relu5_1'
    dim_descriptor = 512

# CAM Extraction

if aggregation_type == 'Online':
    num_classes = 64
elif aggregation_type == 'Offline':
    num_classes = 1000

# Images to load into the net (+ images, + memory, + fast)
batch_size = 12
# Images to pre-load (+ images, + memory, + fast)
image_batch_size = 200
# Dimension of h5 files (+ images, + memory)
descriptors_batch_size = 10000
chunk_index = 0

if dataset == 'distractors100k':
    n_img_dataset = 100070
    train_list_path_h = "/imatge/ajimenez/workspace/ITR/lists/list_oxford105k_horizontal.txt"
    train_list_path_v = "/imatge/ajimenez/workspace/ITR/lists/list_oxford105k_vertical.txt"
    path_descriptors = '/imatge/ajimenez/work/ITR/descriptors100k/descriptors_new/' + model_name + '/' + layer + '/' + dim + '/'
    descriptors_cams_path_wp = path_descriptors + 'distractor_all_' + str(num_classes) + '_wp'
    descriptors_cams_path_mp = path_descriptors + 'distractor_all_' + str(num_classes) + '_mp'
    create_folders(path_descriptors)


def extract_cam_descriptors(model_name, batch_size, num_classes, size, mean_value, image_train_list_path, desc_wp, desc_mp, chunk_index):
    images = [0] * image_batch_size
    image_names = [0] * image_batch_size
    counter = 0
    desc_count = 0
    num_images = 0
    ind = 0
    t0 = time.time()

    print 'Horizontal size: ', size[0]
    print 'Vertical size: ', size[1]

    if model_name == 'Vgg_16_CAM':
        model = VGGCAM(nb_classes, (3, size[1], size[0]))
        model.load_weights(VGGCAM_weight_path)

    print 'Model loaded'

    model.summary()
    for line in open(image_train_list_path):
        if counter >= image_batch_size:
            print 'Processing image batch: ', ind
            t1 = time.time()
            data = preprocess_images(images, size[0], size[1], mean_value)

            if aggregation_type == 'Offline':
                features, cams, cl = \
                    extract_feat_cam(model, layer, batch_size, data, num_classes)
                d_wp = weighted_cam_pooling(features, cams)
                desc_wp = np.concatenate((desc_wp, d_wp))

            elif aggregation_type == 'Online':
                features, cams = extract_feat_cam_all(model, layer, batch_size, data)

                d_wp = weighted_cam_pooling(features, cams)
                for img_ind in range(0, batch_size):
                    #print 'Saved ' + image_names[img_ind] + '.h5'
                    save_data(d_wp[img_ind*nb_classes:(img_ind+1)*nb_classes], path_descriptors,
                              image_names[img_ind]+'.h5')

            print 'Image batch processed, CAMs descriptors obtained!'
            print 'Time elapsed: ', time.time()-t1
            #print desc_wp.shape
            sys.stdout.flush()
            counter = 0
            desc_count += image_batch_size
            if descriptors_batch_size == desc_count and aggregation_type == 'Online':
                print 'Saving ...' + descriptors_cams_path_wp + '_' + str(chunk_index)+'.h5'
                save_data(desc_wp, descriptors_cams_path_wp + '_' + str(chunk_index)+'.h5','')
                desc_count = 0
                chunk_index += 1
                desc_wp = np.zeros((0, dim_descriptor), dtype=np.float32)
                #desc_mp = np.zeros((0, dim_descriptor), dtype=np.float32)
            ind += 1

        line = line.rstrip('\n')
        images[counter] = imread(line)
        if dataset == 'Oxford':
            line = line.replace('/imatge/ajimenez/work/datasets_retrieval/Oxford/1_images/', '')
        elif dataset == 'Paris':
            line = line.replace('/imatge/ajimenez/work/datasets_retrieval/Paris/imatges_paris/', '')
        image_names[counter] = (line.replace('.jpg', ''))
        counter += 1
        num_images += 1

    #Last batch
    print 'Last Batch:'
    data = np.zeros((counter, 3, size[1], size[0]), dtype=np.float32)
    data[0:] = preprocess_images(images[0:counter], size[0], size[1], mean_value)
    if aggregation_type == 'Offline':
        features, cams, cl = extract_feat_cam(model, layer, batch_size, data, num_classes)
        d_wp = weighted_cam_pooling(features, cams)
        desc_wp = np.concatenate((desc_wp, d_wp))
        save_data(desc_wp, descriptors_cams_path_wp + '_' + str(chunk_index) + '.h5', '')
        chunk_index += 1
        desc_wp = np.zeros((0, dim_descriptor), dtype=np.float32)
    elif aggregation_type == 'Online':
        features, cams = extract_feat_cam_all(model, layer, batch_size, data)
        d_wp = weighted_cam_pooling(features, cams)
        for img_ind in range(0, counter):
            save_data(d_wp[img_ind * nb_classes:(img_ind + 1) * nb_classes], path_descriptors,
                      image_names[img_ind] + '.h5')

    print desc_wp.shape
    print 'Batch processed, CAMs descriptors obtained!'
    print 'Total time elapsed: ', time.time() - t0
    sys.stdout.flush()

    return desc_wp, chunk_index


########################################################################################################################
# Main Script

print 'Num classes: ', num_classes
print 'Mean: ', mean_value

t_0 = time.time()
desc_wp = np.zeros((0, dim_descriptor), dtype=np.float32)
desc_mp = np.zeros((0, dim_descriptor), dtype=np.float32)


# Horizontal Images
desc_wp, c_ind = \
    extract_cam_descriptors(model_name, batch_size, num_classes, size_h, mean_value, train_list_path_h, desc_wp, chunk_index)

# Vertical Images
desc_wp, c_ind = \
    extract_cam_descriptors(model_name, batch_size, num_classes, size_v, mean_value, train_list_path_v, desc_wp, c_ind)


print 'Data Saved'
print 'Total time elapsed: ', time.time() - t_0