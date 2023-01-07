# Stable Diffusion extension: Search model

A custom extension for [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) to easier search for a model.

With more and more models I find it increasingly difficult to find the one with the right checksum to follow someone's prompt. Also I get more and more models with the same checksum by now.

To help with this a little, I wrote this simple extension.

After choosing a new grid option in the settings:
<img src="images/extension.jpg"/>

The query wildcard-searches over hash and filename. Results are filtered and the model can be directly loaded by clicking its radio button.

## Installation

The extension can be installed directly from within the **Extensions** tab within the Webui.

You can also install it manually by running the following command from within the webui directory:

	git clone https://github.com/AlUlkesh/sd_search_model/ extensions/sd_search_model

## Limitations
* Not pretty. I haven't found out yet how to do gradio and pretty.
* Haven't found a way to update the model name in the usual dropdown. But the model is being loaded, as can be seen on the "Currently loaded model" field.

