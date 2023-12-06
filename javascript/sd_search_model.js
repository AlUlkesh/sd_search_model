function ssm_delay(ms){return new Promise(resolve => setTimeout(resolve, ms))}

async function ssmOneLineSwitch() {
    await ssm_delay(200)

    const ssm_parent = gradioApp().querySelector("input[name=\'radio-ssm_radio\']").parentElement.parentElement
    if (ssm_parent.style.display == "block") {
        ssm_parent.style.display = ""
    } else {
        ssm_parent.style.display = "block"
    }
}

async function ssmLoadModel(ssm_current_textbox) {
    selectCheckpoint(ssm_current_textbox) // from ui.js
}
