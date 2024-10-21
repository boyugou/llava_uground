import os

import torch
from PIL import Image, ImageDraw

from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates
from llava.mm_utils import tokenizer_image_token, process_images, resize_for_large_image
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init


def draw_circle_on_image(image, coordinates, radius=20, color=(255, 0, 0)):
    x, y = coordinates
    img_width, img_height = image.size

    if not (0 <= x <= img_width):
        return image

    if not (0 <= y <= img_height):
        return image

    draw = ImageDraw.Draw(image)

    left_up_point = (x - radius, y - radius)
    right_down_point = (x + radius, y + radius)

    draw.ellipse([left_up_point, right_down_point], outline=color, width=5)

    return image


disable_torch_init()
model_path = 'osunlp/UGround'
tokenizer, model, image_processor, context_len = load_pretrained_model(model_path, None, model_path)

image_path = "gradio_examples/semantic.jpg"
description = "Home"

qs = f"In the screenshot, where are the pixel coordinates (x, y) of the element corresponding to \"{description}\"?"

qs = DEFAULT_IMAGE_TOKEN + '\n' + qs

conv = conv_templates['llava_v1'].copy()
conv.append_message(conv.roles[0], qs)
conv.append_message(conv.roles[1], None)
prompt = conv.get_prompt()

input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()

image = Image.open(os.path.join(image_path)).convert('RGB')

resized_image, pre_resize_scale = resize_for_large_image(image)
# print("resized_scale: ",pre_resize_scale)

image_tensor, image_new_size = process_images([resized_image], image_processor, model.config)

with torch.inference_mode():
    output_ids = model.generate(
        input_ids,
        images=image_tensor.half().cuda(),
        image_sizes=[image_new_size],
        temperature=0,
        top_p=None,
        num_beams=1,
        max_new_tokens=16384,
        use_cache=True)

outputs = tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
print("resized_outputs:",outputs)

output_coordinates = eval(outputs)
fixed_coordinates = tuple(x / pre_resize_scale for x in output_coordinates)
print("fixed_outputs:",fixed_coordinates)

image = draw_circle_on_image(image, fixed_coordinates)
image.show()
