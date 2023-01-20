from modules.paths import models_path
from modules import script_callbacks
from modules import sd_models
from modules import shared
from modules import ui
import fnmatch
import gradio as gr
import hashlib
import json
import os

def timeout(js):
    # For some reason gradio is not ready yet, when javascript starts, so here's a timeout to make it work
    js_timeout = "setTimeout(function() {" + js + "}, 200)"

    return js_timeout

def hash_display(filename, hash, hash_types):
    display = filename
    split = hash.split(" / ")
    if len(hash_types) > 0:
        display = f"{display} ["
        if "old" in hash_types:
            display = f"{display}{split[0]} / "
        if "sha256" in hash_types:
            display = f"{display}{split[1]} / "
        if "sha256_short" in hash_types:
            display = f"{display}{split[2]} / "
        display = display[:-3] + "]"

    return display

def on_ui_tabs():
    def ssm_choices(hashes, hash_types):
        if hashes:
            choices = []
            for filename, (hash, visible) in hashes.items():
                if visible:
                    display = hash_display(filename, hash, hash_types)
                    choices.append(display)

        return choices

    def ssm_without_hashes(ssm2sd_model_name):
        split = ssm2sd_model_name.split(" [")
        new_name = split[0]
        return new_name

    def ssm_with_hashes(sd2ssm_model_name, ssm_hashes_textbox_value, ssm_hash_version_value):
        hashes = json.loads(ssm_hashes_textbox_value)
        new_name = ""
        for filename, (hash, visible) in hashes.items():
            if filename == sd2ssm_model_name:
                new_name = hash_display(filename, hash, ssm_hash_version_value)
                break

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
        # Get the hashes of each file and store it in a dictionary
        hashes = {}
        for file in model_files:
            with open(file, 'rb') as f:
                # Old hash function, implemented here in case it gets removed
                hash_function = hashlib.sha256()
                f.seek(0x100000)
                hash_function.update(f.read(0x10000))
                hash_old = hash_function.hexdigest()[0:8]
                # New hash function
                hash_new_info = sd_models.CheckpointInfo(file)
                hash_new_info.calculate_shorthash()
                hash_new = hash_new_info.sha256
                hash_new_short = hash_new_info.shorthash
                hash_all = f"{hash_old} / {hash_new} / {hash_new_short}"
                relative_path = os.path.relpath(file, model_path)
                hashes[relative_path] = (hash_all, True)

        return hashes

    def ssm_generate_again(*args):
        hash_types = args[0]
        selected = args[1]
        ssm_trigger1_number = args[2] + 1
        hashes = ssm_generate()
        ssm_hashes_textbox = json.dumps(hashes)
        choices = ssm_choices(hashes, hash_types)

        return ssm_hashes_textbox, gr.update(choices=choices, value=selected), ssm_trigger1_number

    def ssm_search(*args):
        query = args[0]
        hashes = json.loads(args[1])
        hash_types = args[2]
        selected = args[3]
        ssm_trigger1_number = args[4] + 1
        # Check if the query matches any filenames or hashes in the hashes dictionary
        for filename, (hash, visible) in hashes.items():
            query_wildcard = "*" + query + "*"
            if fnmatch.fnmatch(filename, query_wildcard) or fnmatch.fnmatch(hash, query_wildcard):
                hashes[filename] = (hash, True)
            else:
                hashes[filename] = (hash, False)
        choices = ssm_choices(hashes, hash_types)

        return gr.update(choices=choices, value=selected), json.dumps(hashes), ssm_trigger1_number

    def ssm_reset(*args):
        hashes = json.loads(args[0])
        hash_types = args[1]
        selected = args[2]
        ssm_trigger1_number = args[3] + 1
        for filename, (hash, visible) in hashes.items():
                hashes[filename] = (hash, True)
        choices = ssm_choices(hashes, hash_types)

        return gr.update(choices=choices, value=selected), ssm_trigger1_number

    def ssm_hash_version_change(*args):
        hashes = json.loads(args[0])
        hash_types = args[1]
        selected = args[2]
        choices = ssm_choices(hashes, hash_types)

        return gr.update(choices=choices, value=selected)

    def ssm_radio_change(*args):
        choice = args[0]
       
        choice = ssm_without_hashes(choice)
        model_dir = "Stable-diffusion"
        model_path = os.path.abspath(os.path.join(models_path, model_dir, choice))
        choice_checkpoint_info = sd_models.CheckpointInfo(model_path)
        choice_checkpoint_info.register()
        ui.apply_setting("sd_model_checkpoint", choice_checkpoint_info.title)
       
        # Current model format for webui
        choice = ssm_with_hashes(choice, ssm_hashes_textbox.value, ["sha256_short"])

        return choice

    with gr.Blocks() as ssm_interface:
        with gr.Row():
            ssm_query_textbox = gr.Textbox(label="Query", elem_id="ssm_query")
            ssm_search_button = gr.Button(value="Search", elem_id="ssm_search", variant="primary")
            ssm_reset_button = gr.Button(value="Reset Search", elem_id="ssm_reset")
            ssm_generate_button = gr.Button(value='Refresh', elem_id="ssm_generate")

        with gr.Row():
            ssm_current_textbox = gr.Textbox(label="Currently loaded model", elem_id="ssm_current", value=shared.opts.sd_model_checkpoint)
            ssm_trigger1_number = gr.Number(label="ssm_trigger1", elem_id="ssm_trigger1", value=1, visible=False)

        with gr.Row():
            ssm_hashes_textbox = gr.Textbox(label="ssm_hashes", elem_id="ssm_hashes", value=json.dumps(ssm_generate()), visible=False)

        with gr.Row():
            ssm_hash_version_checkbox = gr.CheckboxGroup(label="Hash version", elem_id="ssm_hash_version", choices=("old", "sha256", "sha256_short"), value="old")
            ssm_radio1_button = gr.Button(value="Switch to/from one-line display", elem_id="ssm_radio1")

        with gr.Box():
            ssm_radio = gr.Radio(label="Hash: Filename", elem_id="ssm_radio", choices=ssm_choices(json.loads(ssm_hashes_textbox.value), ssm_hash_version_checkbox.value), value=ssm_with_hashes(shared.opts.sd_model_checkpoint, ssm_hashes_textbox.value, ssm_hash_version_checkbox.value))

        ssm_search_button.click(
            fn=ssm_search,
            inputs=[ssm_query_textbox, ssm_hashes_textbox, ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number],
            outputs=[ssm_radio, ssm_hashes_textbox, ssm_trigger1_number],
        )

        ssm_reset_button.click(
            fn=ssm_reset,
            inputs=[ssm_hashes_textbox, ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number],
            outputs=[ssm_radio, ssm_trigger1_number],
        )

        ssm_generate_button.click(
            fn=ssm_generate_again,
            inputs=[ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number],
            outputs=[ssm_hashes_textbox, ssm_radio, ssm_trigger1_number],
        )

        ssm_current_textbox.change(
            fn=None,
            inputs=[],
            outputs=[],
            _js=timeout('ssm_current_value=gradioApp().getElementById("ssm_current").querySelector("textarea").value;ssm_model_select=gradioApp().querySelectorAll("#setting_sd_model_checkpoint select option"); for (ssm_i=0; ssm_i < ssm_model_select.length; ssm_i++) {if (ssm_model_select[ssm_i].value == ssm_current_value) {ssm_model_select[ssm_i].selected=true; break;}}'),
        )

        ssm_trigger1_number.change(
            fn=None,
            inputs=[],
            outputs=[],
            _js=timeout('ssm_current_value=gradioApp().getElementById("ssm_current").querySelector("textarea").value;ssm_model_select=gradioApp().querySelectorAll("#setting_sd_model_checkpoint select option"); for (ssm_i=0; ssm_i < ssm_model_select.length; ssm_i++) {if (ssm_model_select[ssm_i].value == ssm_current_value) {ssm_model_select[ssm_i].selected=true; break;}}'),
        )

        ssm_hash_version_checkbox.change(
            fn=ssm_hash_version_change,
            inputs=[ssm_hashes_textbox, ssm_hash_version_checkbox, ssm_radio],
            outputs=[ssm_radio],
        )

        ssm_radio1_button.click(
            fn=None,
            inputs=[],
            outputs=[],
            _js=timeout('ssm_class = gradioApp().querySelectorAll(".flex.flex-wrap.gap-2");ssm_class.forEach(function(elem) {radio = elem.querySelectorAll("input[name=\'radio-ssm_radio\']");if (radio.length > 0) {if (elem.style.display == "block"){elem.style.display = "flex"} else {elem.style.display = "block";}}})'),
        )

        ssm_radio.change(
            fn=ssm_radio_change,
            inputs=[ssm_radio],
            outputs=[ssm_current_textbox],
        )

    return [(ssm_interface, "Search model", "ssm_interface")]

script_callbacks.on_ui_tabs(on_ui_tabs)
