import os
import gradio as gr
import io
from pathlib import Path
import select
import shutil
from shutil import rmtree
import subprocess as sp
import sys
import subprocess
from typing import Dict, Tuple, Optional, IO
from colorsys import rgb_to_hsv, hsv_to_rgb
import re
import torch

if torch.cuda.is_available():
  print('Cuda available!')
else:
  print('Cuda not available, please check installation.')

# --- IMPORTANT: Variable to be changed upon local installation ---
blenderinstallationpath = r'blender-3.6.0-linux-x64/blender' # Change to your full blender installation path (make sure it's a raw string)
#-------------------------------------------------------------------^
if not os.path.exists('template.blend'):
  os.system('pip install gdown')
  os.system('gdown --id 1KhTinoIvvYiPYy7VyDMi-R9PikbY9YWW -O template.blend')

# --- Demucs Setup ---

model = "htdemucs"
extensions = ["mp3", "wav", "ogg", "flac"]
two_stems = None

mp3 = True
mp3_rate = 320
float32 = False
int24 = False

filename = ''

def find_files(in_path):
    out = []
    for file in Path(in_path).iterdir():
        if file.suffix.lower().lstrip(".") in extensions:
            out.append(file)
    return out

def copy_process_streams(process: sp.Popen):
    for line in process.stdout:
        sys.stdout.write(line.decode())
    for line in process.stderr:
        sys.stderr.write(line.decode())

def separate(inp=None, outp=None):
    inp = inp or in_path
    outp = outp or out_path
    cmd = ["python", "-m", "demucs.separate", "--device", "cuda", "-o", str(outp), "-n", model]
    if mp3:
        cmd += ["--mp3", f"--mp3-bitrate={mp3_rate}"]
    if float32:
        cmd += ["--float32"]
    if int24:
        cmd += ["--int24"]
    if two_stems is not None:
        cmd += [f"--two-stems={two_stems}"]
    files = [str(f) for f in find_files(inp)]
    if not files:
        print(f"No valid audio files")
        return
    print("Going to separate the files:")
    print('\n'.join(files))
    print("With command: ", " ".join(cmd))
    cmd.append(f'"{files[0]}"')
    finalcmd = ''
    for i in cmd:
       finalcmd += i
       finalcmd += ' '
    os.system(finalcmd)

# --- The script to be run ---

colorlist = [0,0,0,0]
vary = 0.14
flist = ['']*4
fname = ''
option = 'man'
voc = 'Yes'

code = """
import bpy
import colorsys
import os
from mathutils import Vector

#Bass
bpath = r'{}'
branges = [(20,60), (60,100), (100,200), (60,100)]
bn = len(branges)
blist = ['basslight'+str(n) for n in range(1,bn+1)]

#Drums
dpath = r'{}'
dranges = [(20,80), (80,150), (150,250), (250,350), (350,3000), (3000,10000)]
dn = len(dranges)
dlist = ['drums'+str(n) for n in range(1,dn+1)]

#Instrumental
ipath = r'{}'
iranges = [(250,350), (350,550), (550,750), (750,1050), (1050,2000), (2000,3000), (3000,10000)]
iN = len(iranges)
ilist = ['inst'+str(n) for n in range(1,iN+1)]

#Vocals
vpath = r'{}'
vranges = [(20,250), (250,350), (350,550), (550,750), (750,1050), (1050,2000), (2000,3000), (3000,10000)]
vn = len(vranges)
vlist = ['vocals'+str(n) for n in range(1,vn+1)]

bpy.context.scene.frame_set(0)

# Setting colors

allofthelights = [blist, dlist, ilist, vlist]
colors = {}
vary = {}
for l, c in zip(allofthelights, colors):
    for object in l:
        light = bpy.data.objects[object]
        light.data.color = (c[0]/255,c[1]/255,c[2]/255)


# Setting center object

mascots = ['man', 'dragon', 'knight', 'sword', 'rose', 'suzanne (blender monkey)']
chosen = '{}'
for m in mascots:
    obj = bpy.data.objects[m]
    if m == chosen:
        obj.hide_set(False)
        obj.hide_render = False
    else:
        obj.hide_set(True)
        obj.hide_render = True

# The main stuff

def bakefunc(freqs, objlist, path, i, pmin, pmax):
    obj = bpy.data.objects[objlist[i]]
    thingy = obj.data.animation_data.action.fcurves
    fcneeded = thingy.find('energy')
    mod = fcneeded.modifiers[0]
    point = mod.control_points[0]
    point.max = pmax
    point.min = pmin

    #limit = fcneeded.modifiers[2]
    #limit.use_max_y = True
    #limit.max_y = 0.8
    #limit.influence = 0.647

    #Selecting object of interest
    bpy.ops.object.select_all(action = 'DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    #Shifting to graph editor
    area = next(area for area in bpy.context.screen.areas if area.type == 'GRAPH_EDITOR')
    override = bpy.context.copy()
    override['area'] = area
    override['region'] = area.regions[-1]

    #Selecting desired f curve
    for fc in thingy:
        fc.select = False
    fcneeded.select = True

    #Baking process
    bpy.ops.graph.sound_bake(
        override,
        filepath=path,
        low=freqs[i][0],
        high=freqs[i][1],
        attack=0.005,
        release=0.2,
        threshold=0.0,
        use_accumulate=False,
        use_additive=False,
        sthreshold=0.1
    )

for i in range(bn):
    bakefunc(branges, blist, bpath, i, -1250, 1250)

for i in range(dn):
    bakefunc(dranges, dlist, dpath, i, -5000, 4200)

    obj = bpy.data.objects[dlist[i]]
    thingy = obj.animation_data.action.fcurves
    fcneeded = thingy.find('rotation_euler', index=0)
    mod = fcneeded.modifiers[0]
    point = mod.control_points[0]
    point.max = -1.3
    point.min = 1

    #limit = fcneeded.modifiers[2]
    #limit.use_max_y = True
    #limit.max_y = 0.8
    #limit.influence = 0.647

    #Selecting object of interest
    bpy.ops.object.select_all(action = 'DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    #Shifting to graph editor
    area = next(area for area in bpy.context.screen.areas if area.type == 'GRAPH_EDITOR')
    override = bpy.context.copy()
    override['area'] = area
    override['region'] = area.regions[-1]

    #Selecting desired f curve
    for fc in thingy:
        fc.select = False
    fcneeded.select = True

    #Baking process
    bpy.ops.graph.sound_bake(
        override,
        filepath=dpath,
        low=dranges[i][0],
        high=dranges[i][1],
        attack=0.005,
        release=0.2,
        threshold=0.0,
        use_accumulate=False,
        use_additive=False,
        sthreshold=0.1
    )

for i in range(vn):
    if '{}' == 'Yes':
        bakefunc(vranges, vlist, vpath, i, -5000, 4200)
    else:
        bakefunc(vranges, vlist, ipath, i, -6000, 4200)

for i in range(iN):
    bakefunc(iranges, ilist, ipath, i, -5000, 5500)


#Adding the new track to the sequencer and adjusting end frame
sequencer =  bpy.context.scene.sequence_editor
for strip in list(sequencer.sequences_all):  # List to avoid mutation issues
        sequencer.sequences.remove(strip)

sound_strip = sequencer.sequences.new_sound(name = 'New1', filepath = r'{}', channel = 1, frame_start = 0)

bpy.context.scene.frame_end = int(sound_strip.frame_final_duration)

#Moving camera rotation keyframe to end frame
fc = bpy.data.objects['Empty'].animation_data.action.fcurves.find('rotation_euler', index=2)
for keyframe in fc.keyframe_points:
    if keyframe.co.x > 1:
        keyframe.co.x = int(sound_strip.frame_final_duration)
        break
        
# paste here if something goes wrong

sequences = bpy.context.scene.sequence_editor.sequences_all
for strip in sequences:
    if strip.type == 'SOUND':
        sound_data = strip.sound
        if sound_data and not sound_data.packed_file:
            sound_data.pack()


"""
customobjcode = """
# This part of the code configures a custom center object, if chosen.

bpy.ops.object.select_all(action='DESELECT')

# Config
customobjpath = r"{}"
final_name = "usercenterobject"
floor_z = 1.6

customobjpath = os.path.abspath(customobjpath)
ext = os.path.splitext(customobjpath)[1].lower()

# Importing 3D file and joining into a single object

if ext == '.obj':
    bpy.ops.import_scene.obj(filepath=customobjpath)
elif ext == '.stl':
    bpy.ops.import_mesh.stl(filepath=customobjpath)
elif ext == '.fbx':
    bpy.ops.import_scene.fbx(filepath=customobjpath)
    
imported_objs = bpy.context.selected_objects
bpy.ops.object.select_all(action='DESELECT')
numparts = 0
for obj in imported_objs:
    numparts += 1
    obj.select_set(True)
print(numparts)
bpy.context.view_layer.objects.active = imported_objs[0]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
if numparts > 1:
    bpy.ops.object.join()
joined_obj = bpy.context.active_object
joined_obj.name = final_name

#Positioning and scaling object

min_world_z = min((joined_obj.matrix_world @ v.co).z for v in joined_obj.data.vertices)

delta_z = floor_z - min_world_z
joined_obj.location.z += delta_z

bpy.ops.object.select_all(action='DESELECT')
obj = bpy.data.objects[final_name]
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

target_origin_world = Vector((0, 0, floor_z))
target_origin_local = joined_obj.matrix_world.inverted() @ target_origin_world
for v in joined_obj.data.vertices:
    v.co -= target_origin_local
joined_obj.location += target_origin_world

bpy.context.view_layer.objects.active = joined_obj
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

target_height = 4.49432
scale_factor = target_height / joined_obj.dimensions.z
joined_obj.scale *= scale_factor

bpy.ops.object.select_all(action='DESELECT')
joined_obj.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

if joined_obj.dimensions.y > 10:
    scale_factor = 10 / joined_obj.dimensions.y
    joined_obj.scale *= scale_factor
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

if joined_obj.dimensions.x > 10:
    scale_factor = 10 / joined_obj.dimensions.x
    joined_obj.scale *= scale_factor
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

new_mat = bpy.data.materials.new(name="modify_this_if_you_want")
new_mat.use_nodes = False
joined_obj.data.materials.clear()
joined_obj.data.materials.append(new_mat)
joined_obj.active_material = new_mat

"""
# --- Color and center object selection ---


allblack = ['#000000']*4
html_template = """
<p>Color family of the visualizer:</p>
<div style='display: flex; gap: 10px; margin-top: 10px;'>
    <div style='width: 50px; height: 50px; background-color: rgba{}; border: 1px solid #000;'></div>
    <div style='width: 50px; height: 50px; background-color: rgba{}; border: 1px solid #000;'></div>
    <div style='width: 50px; height: 50px; background-color: rgba{}; border: 1px solid #000;'></div>
    <div style='width: 50px; height: 50px; background-color: rgba{}; border: 1px solid #000;'></div>
</div>
"""

def normaliseh(n):
  if n>1:
    n -= 1
  elif n<0:
    n += 1
  return n

def normalisesv(n):
  if n>1:
    n = 1
  elif n<0:
    n = 0
  return n

def alter(color, dh, ds, dv, indexx):
    global hlist, slist, vlist
    if color[0] == '#':
        color = color.lstrip('#')
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        c = (r,g,b)
    else:
        c = eval(color.strip('rgba'))
    h,s,v = rgb_to_hsv(c[0]/255, c[1]/255, c[2]/255)
    h = normaliseh(h+dh)
    s = normalisesv(s+ds)
    v = normalisesv(v+dv)

    r,g,b = hsv_to_rgb(h,s,v)

    colorlist[indexx] = (r*255, g*255, b*255)

    r,g,b = hsv_to_rgb(h,s,v)
    return (r*255, g*255, b*255)

def update_color_blocks(c, var):
    try:
        global vary
        vary = var
        colors = [alter(c,0,0,-0.25,0),alter(c,var,0,0,1),alter(c,-var,0,0,2),alter(c,0,-0.05,0,3)]
        html = html_template.format(*colors)
        return html
    except:
        return f"<h1>Invalid color {c}</h1>"


option = 'man'
choices = ['man', 'dragon', 'knight', 'sword', 'rose', 'suzanne (blender monkey)', 'custom']

def update_selection(selected, visible):
    global option
    ogoption = option
    option = selected
    if selected == 'custom' or ogoption == 'custom':
        return gr.update(visible=not visible), not visible
    else:
        return gr.update(visible=visible), visible

def aretherevocals(selected):
    global voc
    voc = selected


fnamewpath = ''
custommodelpath = ''
def toggle_video(visible):
    return gr.update(visible=not visible), not visible

# --- Handling entire pipeline ---
def handle_upload(file, method, threedpath):
    global fnamewpath
    global flist, fname, vary, option, code, customobjcode
    in_path = Path("tmp_in")
    out_path = Path("separated")
    blend_path = Path("download")
    flist = []

    if option == 'custom':
       code += customobjcode.format(threedpath.name)
    code += "\nbpy.ops.wm.save_as_mainfile(filepath=r'{}')\n"

    if method == 'mp3':
      fnamewpath = Path(file.name)
    elif method == 'link':
        file = file.split('&')[0]
        result = subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "--print", f"%(title)s [{file[-11:]}].mp3", file],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        fnamewspecialchars = result.stdout.strip()
        fname = re.sub(r'[^a-zA-Z0-9]', '', fnamewspecialchars[:-4])
        fname += '.mp3'
        execution = f'yt-dlp -o "{fname}" --extract-audio --audio-format mp3 "{file}"'
        os.system(execution)
        fnamewpath = Path(os.path.abspath(fname))

    fname = fnamewpath.name
    
    if in_path.exists():
        rmtree(in_path)
    in_path.mkdir()

    if out_path.exists():
        rmtree(out_path)
    out_path.mkdir()

    if blend_path.exists():
        rmtree(blend_path)
    blend_path.mkdir()

    target_path = Path(os.path.abspath(in_path / fnamewpath.name))
    print(target_path)
    shutil.copy(fnamewpath, target_path)

    in_path = Path(os.path.abspath(in_path))
    out_path = Path(os.path.abspath(out_path))
    separate(in_path, out_path)

    for f in out_path.rglob("*.mp3"):
      flist.append(str(f))
    flist.sort()

    with open('blendscript.py', 'w') as f:
      f.write(code.format(*[flist[0], flist[1], flist[2], flist[3], colorlist, vary, option, voc, os.path.abspath(f'tmp_in/{fname}'), str(Path(f'{os.path.abspath("download")}') / Path(f'{fname[:-4]}.blend'))]))#  os.path.abspath(f'{fname[:-4]}.blend')]))

    os.system(fr'"{blenderinstallationpath}" -b template.blend --python blendscript.py')

    shutil.make_archive('visualizer', 'zip', 'download')
    return 'visualizer.zip'

# --- Gradio UI ---

modifiedocean = gr.themes.Ocean(
    neutral_hue="zinc",
    text_size=gr.themes.Size(lg="24px", md="18px", sm="10px", xl="30px", xs="12px", xxl="40px", xxs="10px"),
    spacing_size='lg',
    radius_size=gr.themes.Size(lg="20px", md="20px", sm="20px", xl="20px", xs="20px", xxl="20px", xxs="10px")
).set(
    button_primary_background_fill='linear-gradient(120deg, *secondary_600 0%, *primary_100 60%, *primary_200 100%)',
    button_large_radius='*radius_xxl',
    block_radius = '*radius_xxs',
    button_large_text_size='*text_md')

modifiedcitrus = gr.themes.Citrus(
    primary_hue="teal",
    secondary_hue="emerald",
    neutral_hue="gray",
    text_size=gr.themes.Size(lg="24px", md="18px", sm="10px", xl="30px", xs="12px", xxl="40px", xxs="10px"),
    spacing_size='lg',
    radius_size=gr.themes.Size(lg="20px", md="20px", sm="20px", xl="20px", xs="20px", xxl="20px", xxs="10px")
).set(
    button_primary_background_fill='linear-gradient(120deg, *secondary_600 0%, *primary_100 60%, *primary_200 100%)',
    button_large_radius='*radius_xxl',
    block_radius = '*radius_xxs',
    button_large_text_size='*text_md')

css_reset = """
<style>
  html, body {
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden;
    box-sizing: border-box;
  }

  #root, .gradio-container {
    margin: 10px auto auto auto !important;  /* top right bottom left */
    padding: 0 !important;
    width: 85% !important;
    box-sizing: border-box;
  }

  .gr-block.gr-box:first-child,
  .gr-markdown:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }
  #filedownload {
    margin: 73px 0 0 0 !important;
  }
  #rounded {
  border-radius:20px;
  }
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

body, #root, .gradio-container {
  animation: fadeIn 1s ease-in-out;
}
</style>
"""

demo = gr.Blocks(theme=modifiedcitrus)
with demo:
  gr.HTML(css_reset)
  gr.Markdown("# BlendViz: Experience Your Music.")
  gr.Markdown("You are about to create a three dimensional music visualizer powered by Demucs for stem splitting and Blender for visualization. Choose a song either by uploading an mp3 file or by pasting a Youtube link. Set your desired color, choose your center object and click on Generate. Once done, the blender file of the visualiser can be downloaded. Refer to the file itself for further instructions. Please note that **you must have Blender installed** to be able to open the file. Generation will take 2-3 minutes on Colab's T4 GPU.")
  with gr.Row():
    with gr.Column():
      toggle_btn = gr.Button("View Demo")
      video = gr.Video(value = 'https://drive.google.com/uc?export=download&id=1JhyCAybqMjtB7eiEEKwSeo9eF7bwrS2m', visible = False, label = "Press again to hide")
      state = gr.State(value=False)
      toggle_btn.click(fn=toggle_video, inputs=state, outputs=[video, state])
    with gr.Column():
      pass
  with gr.Row():
    with gr.Column():
     with gr.Group(elem_id='rounded'):
      gr.Markdown("### <div style = 'text-align:center; padding:15px;'>Choose a Color</div>")
      with gr.Row(scale=1):
        color = gr.ColorPicker(label="Kindly choose at least once to register a color.")
      with gr.Row(scale=1):
        slider = gr.Slider(label="Adjust this slider to vary color hue.", minimum=0, maximum=0.5, step=0.01, value=0.14)
      with gr.Row(scale=1):
        output = gr.HTML(html_template.format(*allblack))
    with gr.Column():
     with gr.Group(elem_id='rounded'):
      gr.Markdown("### <div style = 'text-align:center; padding:15px;'>Choose a Center Object </div>")
      radio = gr.Radio(choices, label='Choose custom to upload your own 3D model.', value='man')
      customobj = gr.File(label='Supported formats: .stl, .fbx, .obj ONLY', visible=False)
      customornot = gr.State(value=False)
      radio.change(fn=update_selection, inputs=[radio, customornot], outputs=[customobj, customornot])
  with gr.Group(elem_id = 'rounded'):
    vocradio = gr.Radio(['Yes', 'No'], label = 'Do vocals play a significant role in your song? If unsure, select No.', value='Yes')
    vocradio.change(fn=aretherevocals, inputs=vocradio)
  with gr.Row():
    with gr.Column():
      with gr.Tab('mp3'):
        audio_input = gr.File(label="Upload audio", type="filepath")
        split_btn = gr.Button("Generate")
      with gr.Tab('link'):
        yt_input = gr.Textbox(label="Paste a youtube link:")
        gr.Markdown("*(May trigger an error if downloads are blocked by Youtube. In that case, please upload an mp3 file.)*")
        yt_btn = gr.Button("Generate")
    with gr.Column():
      output_download = gr.File(label="Download visualizer", elem_id = 'filedownload')

  gr.Markdown("*(If downloading the final blender file takes too long, download directly from the colab notebook. If running locally, the final file is directly accessible.)*")  
  color.change(update_color_blocks, inputs=[color, slider], outputs=output)
  slider.change(update_color_blocks, inputs=[color, slider], outputs=output)
  split_btn.click(fn=lambda val, objfile: handle_upload(val, 'mp3', objfile), inputs=[audio_input, customobj], outputs=output_download)
  yt_btn.click(fn=lambda val2, objfile: handle_upload(val2, 'link', objfile), inputs=[yt_input, customobj], outputs=output_download)
try:
  demo.launch(share=True)
except:
  demo.launch()
