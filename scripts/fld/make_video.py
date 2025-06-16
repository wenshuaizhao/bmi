import cv2
import os

# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/flat_mit_humanoid/fld/dynamics_training/20240423155422/exported/frames'
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/original_data/20240515090951'
image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/play_fld/20240529135605_scae'
video_name = image_folder+'/video.mp4'



images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
images.sort(key=lambda f: int(f.split('.')[0]))
frame = cv2.imread(os.path.join(image_folder, images[0]))
height, width, layers = frame.shape

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 'mp4v' for MP4 format
# out = cv2.VideoWriter('output.mp4', fourcc, 24, (640, 480))

# video = cv2.VideoWriter(video_name, 0, 24, (width,height))
video = cv2.VideoWriter(video_name, fourcc, 24, (width,height))

for image in images:
    video.write(cv2.imread(os.path.join(image_folder, image)))
    print(f'reading image {image}')
cv2.destroyAllWindows()
video.release()