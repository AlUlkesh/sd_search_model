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

async function ssmLoadModel() {
    /*
    await ssm_delay(200)
    const ssm_current_value=gradioApp().getElementById("ssm_current").querySelector("textarea").value
    const ssm_model_select=gradioApp().querySelector("#setting_sd_model_checkpoint")
    const ssm_model_select_models=ssm_model_select.querySelectorAll(".single-select")
    ssm_model_select_models.forEach(function(ssm_model) {
        if (ssm_model.firstChild.textContent == ssm_current_value) {
            ssm_model.selected = true
        }
    })
    */
}
