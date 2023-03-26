from modules.paths import models_path
from modules import script_callbacks
from modules import sd_models
from modules import shared
from modules import ui
import fnmatch
import gradio as gr
import hashlib
import os

class Hashes:
    hashes_dict = {}
    def __init__(self, filename=None, modification_time=None, filesize = None, hash_old=None, hash_new=None, hash_new_short=None, visible=None):
        self.filename = filename
        self.modification_time = modification_time
        self.filesize = filesize
        self.hash_old = hash_old
        self.hash_new = hash_new
        self.hash_new_short = hash_new_short
        self.visible = visible
        self.__class__.hashes_dict[filename] = self

def timeout(js):
    # For some reason gradio is not ready yet, when javascript starts, so here's a timeout to make it work
    js_timeout = "setTimeout(function() {" + js + "}, 200)"

    return js_timeout

def hash_display(filename, hash_old, hash_new, hash_new_short, hash_types):
    display = filename
    if len(hash_types) > 0:
        display = f"{display} ["
        if "old" in hash_types:
            display = f"{display}{hash_old} / "
        if "sha256" in hash_types:
            display = f"{display}{hash_new} / "
        if "sha256_short" in hash_types:
            display = f"{display}{hash_new_short} / "
        display = display[:-3] + "]"

    return display

def on_ui_tabs():
    def ssm_choices(hash_types, sort_option):
        choices = []

        if sort_option == "size":
            Hashes.hashes_dict=dict(sorted(Hashes.hashes_dict.items(), key=lambda x: x[1].filesize, reverse=True))
        elif sort_option == "time":
            Hashes.hashes_dict=dict(sorted(Hashes.hashes_dict.items(), key=lambda x: x[1].modification_time, reverse=True))
        else:
            Hashes.hashes_dict=dict(sorted(Hashes.hashes_dict.items(), key=lambda x: x[1].filename.lower(), reverse=False))

        for hashes in Hashes.hashes_dict.values():
            if hashes.visible:
                display = hash_display(hashes.filename, hashes.hash_old, hashes.hash_new, hashes.hash_new_short, hash_types)
                choices.append(display)

        return choices

    def ssm_without_hashes(model_name):
        split = model_name.split(" [")
        new_name = split[0]
        return new_name

    def ssm_with_hashes(model_name, ssm_hash_version_value):
        new_name = ""
        for hashes in Hashes.hashes_dict.values():
            if hashes.filename == model_name:
                new_name = hash_display(hashes.filename, hashes.hash_old, hashes.hash_new, hashes.hash_new_short, ssm_hash_version_value)
                break

        return new_name

    def ssm_generate(*args):
        # Get the list of all model-files in the directory tree
        model_dir = "Stable-diffusion"
        ckpt_dir = os.path.abspath(os.path.join(shared.cmd_opts.ckpt_dir or models_path, model_dir))
        model_files = []
        for dirpath, dirnames, filenames in os.walk(ckpt_dir):
            for file in filenames:
                if file.endswith('.ckpt') or file.endswith('.safetensors'):
                    model_files.append(os.path.join(dirpath, file))
        # Get the hashes of each file and store them in Hashes class
        Hashes.hashes_dict.clear()
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
                relative_path = os.path.relpath(file, ckpt_dir)
                stats = os.stat(file)
                modification_time = stats.st_mtime
                filesize = stats.st_size
                hashes = Hashes(filename=relative_path, modification_time=modification_time, filesize=filesize, hash_old=hash_old, hash_new=hash_new, hash_new_short=hash_new_short, visible=True)

        return hashes

    def ssm_generate_again(*args):
        hash_types = args[0]
        selected = args[1]
        ssm_trigger1_number = args[2] + 1
        sort_option = args[3]
        hashes = ssm_generate()
        choices = ssm_choices(hash_types, sort_option)

        return gr.update(choices=choices, value=selected), ssm_trigger1_number

    def ssm_search(*args):
        query = args[0]
        hash_types = args[1]
        selected = args[2]
        ssm_trigger1_number = args[3] + 1
        sort_option = args[4]
        search_options = args[5]

        search_filename = False
        search_hash_old = False
        search_hash_new = False
        search_hash_new_short = False
        if "name" in search_options:
            search_filename = True
        if ("only in displayed hashes" in search_options and "old" in hash_types) or ("only in displayed hashes" not in search_options):
            search_hash_old = True
        if ("only in displayed hashes" in search_options and "sha256" in hash_types) or ("only in displayed hashes" not in search_options):
            search_hash_new = True
        if ("only in displayed hashes" in search_options and "sha256_short" in hash_types) or ("only in displayed hashes" not in search_options):
            search_hash_new_short = True

        # Check if the query matches any filenames or hashes in the hashes dictionary
        for hashes in Hashes.hashes_dict.values():
            query_wildcard = "*" + query + "*"
            if  ((search_filename and fnmatch.fnmatch(hashes.filename, query_wildcard)) or
                (search_hash_old and fnmatch.fnmatch(hashes.hash_old, query_wildcard)) or
                (search_hash_new and fnmatch.fnmatch(hashes.hash_new, query_wildcard)) or
                (search_hash_new_short and fnmatch.fnmatch(hashes.hash_new_short, query_wildcard))):
                hashes.visible = True
            else:
                hashes.visible = False
        choices = ssm_choices(hash_types, sort_option)

        return gr.update(choices=choices, value=selected), ssm_trigger1_number

    def ssm_reset(*args):
        hash_types = args[0]
        selected = args[1]
        ssm_trigger1_number = args[2] + 1
        sort_option = args[3]
        for hashes in Hashes.hashes_dict.values():
                hashes.visible = True
        choices = ssm_choices(hash_types, sort_option)

        return gr.update(choices=choices, value=selected), ssm_trigger1_number

    def ssm_hash_version_change(*args):
        hash_types = args[0]
        selected = args[1]
        sort_option = args[2]
        choices = ssm_choices(hash_types, sort_option)

        return gr.update(choices=choices, value=selected)

    def ssm_sort_change(*args):
        sort_option = args[0]
        hash_types = args[1]
        selected = args[2]
        choices = ssm_choices(hash_types, sort_option)

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
        choice = ssm_with_hashes(choice, ["sha256_short"])

        return choice

    with gr.Blocks() as ssm_interface:
        with gr.Row():
            with gr.Column(scale=80):
                ssm_query_textbox = gr.Textbox(label="Query", elem_id="ssm_query")
            with gr.Column(scale=1):
                ssm_search_options_checkbox = gr.CheckboxGroup(label="Search in", elem_id="ssm_search_options", choices=("name", "only in displayed hashes"), value=["name", "only in displayed hashes"])
            with gr.Column(scale=1):
                ssm_search_button = gr.Button(value="Search", elem_id="ssm_search", variant="primary")
            with gr.Column(scale=1):
                ssm_reset_button = gr.Button(value="Reset Search", elem_id="ssm_reset")
            with gr.Column(scale=1):
                ssm_generate_button = gr.Button(value='Refresh', elem_id="ssm_generate")

        with gr.Row():
            ssm_current_textbox = gr.Textbox(label="Currently loaded model", elem_id="ssm_current", value=shared.opts.sd_model_checkpoint)
            ssm_trigger1_number = gr.Number(label="ssm_trigger1", elem_id="ssm_trigger1", value=1, visible=False)

        with gr.Row():
            ssm_hash_version_checkbox = gr.CheckboxGroup(label="Hash version", elem_id="ssm_hash_version", choices=("old", "sha256", "sha256_short"), value="old")
            ssm_radio1_button = gr.Button(value="Switch to/from one-line display", elem_id="ssm_radio1")

        with gr.Row():
            ssm_sort_radio = gr.Radio(label="Sort by", elem_id="ssm_sort", choices=("name", "time", "size"), value="name")

        with gr.Box():
            ssm_generate()
            ssm_radio = gr.Radio(label="Filename [Hashes]", elem_id="ssm_radio", choices=ssm_choices(ssm_hash_version_checkbox.value, ssm_sort_radio.value), value=ssm_with_hashes(shared.opts.sd_model_checkpoint, ssm_hash_version_checkbox.value))

        ssm_search_button.click(
            fn=ssm_search,
            inputs=[ssm_query_textbox, ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number, ssm_sort_radio, ssm_search_options_checkbox],
            outputs=[ssm_radio, ssm_trigger1_number],
        )

        ssm_reset_button.click(
            fn=ssm_reset,
            inputs=[ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number, ssm_sort_radio],
            outputs=[ssm_radio, ssm_trigger1_number],
        )

        ssm_generate_button.click(
            fn=ssm_generate_again,
            inputs=[ssm_hash_version_checkbox, ssm_radio, ssm_trigger1_number, ssm_sort_radio],
            outputs=[ssm_radio, ssm_trigger1_number],
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
            inputs=[ssm_hash_version_checkbox, ssm_radio, ssm_sort_radio],
            outputs=[ssm_radio],
        )

        ssm_sort_radio.change(
            fn=ssm_sort_change,
            inputs=[ssm_sort_radio, ssm_hash_version_checkbox, ssm_radio],
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
