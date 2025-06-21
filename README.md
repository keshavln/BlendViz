# BlendViz

BlendViz is a tool that allows users to visualize their music through an immersive 3D animated lightshow.

[View a demo here.](https://drive.google.com/file/d/1JhyCAybqMjtB7eiEEKwSeo9eF7bwrS2m/view?usp=sharing)

This project uses Demucs by Facebook Research for stem-splitting, and Blender for visualization. The user first chooses a song by either uploading an mp3 file or pasting a Youtube link. They are then allowed to customise the look of their visualizer. The output is a Blender file which can be downloaded. This gives users the freedom to make further modifications to the 3D environment however they deem fit, before the animation is rendered. Please note that **the user must have Blender installed** to be able to open the file.

Use BlendViz via the official [Colab notebook](https://colab.research.google.com/drive/1ZDOBFqAzXyAGvg10-hDJlCN9QVqyrlmF?usp=sharing)

## Local Setup

For those interested, local setup of BlendViz is recommended if a CUDA-enabled GPU is available. Follow the below steps to run BlendViz locally.

1. Clone the repository and set working directory:\
   ``` git clone https://github.com/keshavln/BlendViz ```\
   ``` cd BlendViz ```
2. Create and activate a virtual environment. Ensure that CUDA is installed and available.
3. Install dependencies.
   ``` pip install -r requirements.txt ```\
4. Edit the ```blenderinstallationpath``` variable at line 22 of ```app.py``` to store your current Blender installation path. Please note that Blender 4 cannot be used to run BlendViz. However, the output file may be viewed on any version of blender.
5. Run ```python app.py``` to launch the interface.

Steps 1-4 above involve initial setup. Once completed, it is enough to run the below two commands whenever using BlendViz in the future:\
```cd BlendViz```\
```python app.py```
