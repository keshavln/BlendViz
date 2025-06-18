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

os.environ["PATH"] = os.getcwd() + "/blender-3.6.0-linux-x64:" + os.environ["PATH"]

os.system('pip install gdown')
os.system('gdown --id 1E0MFshpgiinCGpmSsMywIV87gkVEEWa6 -O template.blend')

#Demucs Paramters

model = "htdemucs"
extensions = ["mp3", "wav", "ogg", "flac"]
two_stems = None

mp3 = True
mp3_rate = 320
float32 = False
int24 = False

filename = ''

#Demucs setup functions

def find_files(in_path):
    out = []
    for file in Path(in_path).iterdir():
        if file.suffix.lower().lstrip(".") in extensions:
            out.append(file)
    return out

def copy_process_streams(process: sp.Popen):
    def raw(stream: Optional[IO[bytes]]) -> IO[bytes]:
        assert stream is not None
        if isinstance(stream, io.BufferedIOBase):
            stream = stream.raw
        return stream

    p_stdout, p_stderr = raw(process.stdout), raw(process.stderr)
    stream_by_fd: Dict[int, Tuple[IO[bytes], io.StringIO, IO[str]]] = {
        p_stdout.fileno(): (p_stdout, sys.stdout),
        p_stderr.fileno(): (p_stderr, sys.stderr),
    }
    fds = list(stream_by_fd.keys())

    while fds:
        # `select` syscall will wait until one of the file descriptors has content.
        ready, _, _ = select.select(fds, [], [])
        for fd in ready:
            p_stream, std = stream_by_fd[fd]
            raw_buf = p_stream.read(2 ** 16)
            if not raw_buf:
                fds.remove(fd)
                continue
            buf = raw_buf.decode()
            std.write(buf)
            std.flush()

def separate(inp=None, outp=None):
    inp = inp or in_path
    outp = outp or out_path
    cmd = ["python3", "-m", "demucs.separate", "-o", str(outp), "-n", model]
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
        print(f"No valid audio files in {in_path}")
        return
    print("Going to separate the files:")
    print('\n'.join(files))
    print("With command: ", " ".join(cmd))
    p = sp.Popen(cmd + files, stdout=sp.PIPE, stderr=sp.PIPE)
    copy_process_streams(p)
    p.wait()
    if p.returncode != 0:
        print("Command failed, something went wrong.")

#The script to be run
colorlist = [0,0,0,0]
vary = 0.14
flist = ['']*4
fname = ''
option = 'man'
voc = 'Yes'

code = """
import bpy
import colorsys
#Bass
bpath = '{}'
branges = [(20,60), (60,100), (100,200), (60,100)]
bn = len(branges)
blist = ['basslight'+str(n) for n in range(1,bn+1)]

#Drums
dpath = '{}'
dranges = [(20,80), (80,150), (150,250), (250,350), (350,3000), (3000,10000)]
dn = len(dranges)
dlist = ['drums'+str(n) for n in range(1,dn+1)]

#Instrumental
ipath = '{}'
iranges = [(250,350), (350,550), (550,750), (750,1050), (1050,2000), (2000,3000), (3000,10000)]
iN = len(iranges)
ilist = ['inst'+str(n) for n in range(1,iN+1)]

#Vocals
vpath = '{}'
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
        bakefunc(vranges, vlist, ipath, i, -6000, 3000)

for i in range(iN):
    bakefunc(iranges, ilist, ipath, i, -5000, 5500)


#Adding the new track to the sequencer and adjusting end frame
sequencer =  bpy.context.scene.sequence_editor
for strip in list(sequencer.sequences_all):  # List to avoid mutation issues
        sequencer.sequences.remove(strip)

sound_strip = sequencer.sequences.new_sound(name = 'New1', filepath = 'tmp_in/{}', channel = 1, frame_start = 0)

bpy.context.scene.frame_end = int(sound_strip.frame_final_duration)

#Moving camera rotation keyframe to end frame
fc = bpy.data.objects['Empty'].animation_data.action.fcurves.find('rotation_euler', index=2)
for keyframe in fc.keyframe_points:
    if keyframe.co.x > 1:
        keyframe.co.x = int(sound_strip.frame_final_duration)
        break

'''
# Reference the latest sound strip
sound_strip = bpy.context.scene.sequence_editor.sequences_all[-1]

# Pack its audio only
sound_data = sound_strip.sound
if sound_data and not sound_data.packed_file:
    sound_data.pack()'''

sequences = bpy.context.scene.sequence_editor.sequences_all
for strip in sequences:
    if strip.type == 'SOUND':
        sound_data = strip.sound
        if sound_data and not sound_data.packed_file:
            sound_data.pack()



bpy.ops.wm.save_as_mainfile(filepath='/content/BlendViz/download/{}.blend')
"""

#Color and center object selection


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
    #hlist[indexx] = h
    #slist[indexx] = s
    #vlist[indexx] = v

    r,g,b = hsv_to_rgb(h,s,v)
    #newcode = '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
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
choices = ['man', 'dragon', 'knight', 'sword', 'rose', 'suzanne (blender monkey)']

def update_selection(selected):
    global option
    option = selected

def aretherevocals(selected):
    global voc
    voc = selected

#Stem splitting


fnamewpath = ''
def toggle_video(visible):
    return gr.update(visible=not visible), not visible

def handle_upload(file, method):
    global fnamewpath
    # file is a Gradio UploadedFile object (e.g. tempfile)
    global flist, fname, vary, option
    in_path = Path("tmp_in")
    out_path = Path("separated")
    blend_path = Path("/content/BlendViz/download")
    flist = []

    if method == 'mp3':
      fnamewpath = Path(file.name)
    elif method == 'link':
        os.system(f'yt-dlp -x --audio-format mp3 "{file}"')
        result = subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "--print", f"%(title)s [{file[-11:]}].mp3", file],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        fname = result.stdout.strip()
        fnamewpath = Path('/content/BlendViz') / fname
        #fnamewpath = os.path.abspath(filename)
    fname = fnamewpath.name
    # Ensure clean dirs
    if in_path.exists():
        rmtree(in_path)
    in_path.mkdir()

    if out_path.exists():
        rmtree(out_path)
    out_path.mkdir()

    if blend_path.exists():
        rmtree(blend_path)
    blend_path.mkdir()

    # Copy uploaded file into input folder expected by your demucs runner
    target_path = in_path / fnamewpath.name
    print(target_path)
    shutil.copy(fnamewpath, target_path)

    # Run your original function
    separate(in_path, out_path)

    for f in out_path.rglob("*.mp3"):
      flist.append(str(f))
    flist.sort()

    with open('blendscript.py', 'w') as f:
      f.write(code.format(*[flist[0], flist[1], flist[2], flist[3], colorlist, vary, option, voc, fname, fname[:-4]]))

    os.system("blender-3.6.0-linux-x64/blender -b template.blend --python blendscript.py")

    shutil.make_archive('/content/BlendViz/visualizer', 'zip', '/content/BlendViz/download')
    #return f'/content/BlendViz/download/{fname[:-4]}.blend'
    return '/content/BlendViz/visualizer.zip'

#Gradio UI

modifiedocean = gr.themes.Ocean(
    neutral_hue="zinc",
    text_size=gr.themes.Size(lg="24px", md="18px", sm="10px", xl="30px", xs="12px", xxl="40px", xxs="10px"),
    spacing_size="lg",
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
    margin: 10px 100px 100px 100px !important;  /* top right bottom left */
    padding: 0 !important;
    max-width: 100% !important;
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
</style>
"""

demo = gr.Blocks(theme=modifiedocean)
with demo:
  gr.HTML(css_reset)
  gr.Markdown("# BlendViz: Experience Your Music.")
  gr.Markdown("You are about to create a three dimensional music visualizer powered by Demucs for stem splitting and Blender for visualization. Choose a song either by uploading an mp3 file or by pasting a Youtube link, set your desired color, choose your center object and click on Generate. The movement and intensities of the lights will be tailored to your song. Once done, the blender file of the visualiser can be downloaded. Refer to the file itself for further instructions. Please note that **you must have Blender installed** to be able to open the file. Generation will take 2-3 minutes on Colab's T4 GPU.")
  #gr.Markdown()
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
      gr.Markdown("### Choose a Color")
      with gr.Row(scale=1):
        color = gr.ColorPicker(label="Kindly choose at least once to register a color.")
      with gr.Row(scale=1):
        slider = gr.Slider(label="Adjust this slider to vary color hue.", minimum=0, maximum=0.5, step=0.01, value=0.14)
      with gr.Row(scale=1):
        output = gr.HTML(html_template.format(*allblack))
    with gr.Column():
      gr.Markdown("### Choose a Center Object")
      radio = gr.Radio(choices, label='', value='man')
      radio.change(fn=update_selection, inputs=radio)
  with gr.Row():
    vocradio = gr.Radio(['Yes', 'No'], label = 'Do vocals play a significant role in your song? If unsure, select No.', value='Yes')
    vocradio.change(fn=aretherevocals, inputs=vocradio)
  with gr.Row():
    with gr.Column():
      with gr.Tab('mp3'):
        audio_input = gr.File(label="Upload audio", type="filepath")
        split_btn = gr.Button("Generate")
      with gr.Tab('link'):
        yt_input = gr.Textbox(label="Paste a youtube link:")
        yt_btn = gr.Button("Generate")
    with gr.Column():
      output_download = gr.File(label="Download visualizer", elem_id = 'filedownload')

  gr.Markdown("*(If downloading the final blender file takes too long, download directly from the colab notebook.)*")  
  color.change(update_color_blocks, inputs=[color, slider], outputs=output)
  slider.change(update_color_blocks, inputs=[color, slider], outputs=output)
  #split_btn = gr.Button("Generate")
  split_btn.click(fn=lambda val: handle_upload(val, 'mp3'), inputs=audio_input, outputs=output_download)
  yt_btn.click(fn=lambda val2: handle_upload(val2, 'link'), inputs=yt_input, outputs=output_download)

demo.launch(share=True)
