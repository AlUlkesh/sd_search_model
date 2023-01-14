from modules.paths import models_path
from modules import script_callbacks
from modules import sd_models
from modules import shared
import datetime
import fnmatch
import gradio as gr
import hashlib
import json
import time
import os
import re

def on_ui_tabs():
    def ssm_choices(hashes):
        if hashes:
            choices = []
            for filename, (hash, visible) in hashes.items():
                if visible:
                    choices.append(f"{hash}: {filename}")

        return choices

    def ssm_model_ssm2sd(ssm2sd_model_name):
        split = ssm2sd_model_name.split(":")
        hash = split[0]
        filename = split[1].strip()
        if "[" in shared.opts.sd_model_checkpoint and "]" in shared.opts.sd_model_checkpoint:
            new_name = f"{filename} [{hash}]"
        else:
            new_name = f"{filename}]"
        return new_name

    def ssm_model_sd2ssm(sd2ssm_model_name):
        if "[" in sd2ssm_model_name and "]" in sd2ssm_model_name:
            split = re.split(r'[\[\]]', sd2ssm_model_name)
            new_name = f"{split[1]}: {split[0].strip()}"
        else:
            new_name = sd2ssm_model_name
        return new_name

    def ssm_generate(*args):
        # Get the list of all model-files in the directory tree
        model_dir = "Stable-diffusion"
        model_path = os.path.abspath(os.path.join(models_path, model_dir))
        model_files = []
        for dirpath, dirnames, filenames in os.walk(model_path):
            for file in filenames:
                if file.endswith('.ckpt') or file.endswith('.safetensors'):
                    model_files.append(os.path.join(dirpath, file))
        # Calculate the hash of each file and store it in a dictionary
        hashes = {}
        for file in model_files:
            with open(file, 'rb') as f:
                hash_function = hashlib.sha256()
                f.seek(0x100000)
                hash_function.update(f.read(0x10000))
                relative_path = os.path.relpath(file, model_path)
                hashes[relative_path] = (hash_function.hexdigest()[0:8], True)

        return hashes

    def ssm_generate_again(*args):
        hashes = ssm_generate()
        ssm_hashes_textbox = json.dumps(hashes)
        choices = ssm_choices(hashes)

        return ssm_hashes_textbox, gr.update(choices=choices)

    def ssm_search(*args):
        query = args[0]
        hashes = json.loads(args[1])
        # Check if the query matches any filenames or hashes in the hashes dictionary
        for filename, (hash, visible) in hashes.items():
            query_wildcard = "*" + query + "*"
            if fnmatch.fnmatch(filename, query_wildcard) or fnmatch.fnmatch(hash, query_wildcard):
                hashes[filename] = (hash, True)
            else:
                hashes[filename] = (hash, False)
        choices = ssm_choices(hashes)

        return gr.update(choices=choices)

    def ssm_reset(*args):
        hashes = json.loads(args[0])
        for filename, (hash, visible) in hashes.items():
                hashes[filename] = (hash, True)
        choices = ssm_choices(hashes)

        return gr.update(choices=choices)

    def ssm_radio_change(*args):
        choice = args[0]

        # All these versions seem to work, but none changes the value in the drop down :(
        #shared.sd_model = filename
        #sd_models.reload_model_weights()
        #ui.apply_setting("sd_model_checkpoint", filename)
        #shared.opts.onchange("sd_model_checkpoint", wrap_queued_call(lambda: sd_models.reload_model_weights()))
        shared.opts.sd_model_checkpoint = ssm_model_ssm2sd(choice)
        sd_models.reload_model_weights()
       
        return choice

    with gr.Blocks() as ssm_interface:
        with gr.Row():
            ssm_query_textbox = gr.Textbox(label="Query", elem_id="ssm_query")
            ssm_search_button = gr.Button(value="Search", elem_id="ssm_search", variant="primary")
            ssm_reset_button = gr.Button(value="Reset", elem_id="ssm_reset")
            ssm_generate_button = gr.Button(value='Generate', elem_id="ssm_generate")

        with gr.Row():
            ssm_current_textbox = gr.Textbox(label="Currently loaded model", elem_id="ssm_current", value=ssm_model_sd2ssm(shared.opts.sd_model_checkpoint))

        with gr.Row():
            ssm_hashes_textbox = gr.Textbox(label="ssm_hashes", elem_id="ssm_hashes", value=json.dumps(ssm_generate()), visible=False)

        with gr.Box():
            ssm_radio = gr.Radio(label="Hash: Filename", elem_id="ssm_radio", choices=ssm_choices(json.loads(ssm_hashes_textbox.value)))

        ssm_search_button.click(
            fn=ssm_search,
            inputs=[ssm_query_textbox, ssm_hashes_textbox],
            outputs=[ssm_radio],
        )

        ssm_reset_button.click(
            fn=ssm_reset,
            inputs=[ssm_hashes_textbox],
            outputs=[ssm_radio],
        )

        ssm_generate_button.click(
            fn=ssm_generate_again,
            inputs=[],
            outputs=[ssm_hashes_textbox, ssm_radio],
        )

        ssm_radio.change(
            fn=ssm_radio_change,
            inputs=[ssm_radio],
            outputs=[ssm_current_textbox],
        )

    return [(ssm_interface, "Search model", "ssm_interface")]

script_callbacks.on_ui_tabs(on_ui_tabs)
