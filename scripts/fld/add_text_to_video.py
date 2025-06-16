import cv2
import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/flat_mit_humanoid/fld/dynamics_training/20240423155422/exported/frames'
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/original_data/20240515090951'
motions=['run', 'jog', 'step fast', 'jump', 'spin kick', 'back', 'side left', 'jog slow', 'side right', 'cross over', 'kick', 'stride', 'step']
motion_length=190
# motion_length=240
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/play_fld/20240529135605_scae'
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/play_fld/20240515083030_fld'
# image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/original_data/20240515090951'
image_folder = '/home/username/Downloads/Projects/humanoid/fld/logs/videos/play_fld/20240804172309_full_motions_bmi_add_block'
path = Path(image_folder)
video_folder=path.parent.absolute()
video_name = os.path.join(video_folder, 'video_with_text.mp4')



images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
images.sort(key=lambda f: int(f.split('.')[0]))
frame = cv2.imread(os.path.join(image_folder, images[0]))
height, width, layers = frame.shape

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 'mp4v' for MP4 format
# out = cv2.VideoWriter('output.mp4', fourcc, 24, (640, 480))

# video = cv2.VideoWriter(video_name, 0, 24, (width,height))
video = cv2.VideoWriter(video_name, fourcc, 24, (width,height))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 2
font_color = (255, 255, 255)  # White color in BGR
thickness = 2
line_type = cv2.LINE_AA

# Define the position (bottom-left corner of the text)
text_position = (50, 50)  # Update this to change text position

i=0
for image in images:
    motion_idx=int(i/motion_length)
    text=motions[motion_idx]
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x = (width - text_width) // 2
    y = text_height + 20  # A little padding from the top
    text_position=(x,y)
    i+=1
    # print(text)
    img=cv2.imread(os.path.join(image_folder, image))
    # Add text to the image
    cv2.putText(img, text, text_position, font, font_scale, font_color, thickness, line_type)
    
    video.write(img)
    print(f'reading image {image}')
cv2.destroyAllWindows()
video.release()