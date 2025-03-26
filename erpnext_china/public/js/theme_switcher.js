frappe.provide("frappe.ui");

frappe.ui.ThemeSwitcher = class CustomThemeSwitcher extends frappe.ui.ThemeSwitcher {
    constructor() {
        super()
    }

    fetch_themes() {
		return new Promise((resolve) => {
			this.themes = [
				{
					name: "light",
					label:__("Frappe Light"),
					info:("Light Theme"),
				},
				{
					name: "dark",
					label:__("Timeless Night"),
					info:"Dark Theme",
				},
				{
					name: "automatic",
					label:__("Automatic"),
					info:"Uses system's theme to switch between light and dark mode",
				},
                {
                    name:"ai_era",
                    label: __("AI Era"),
                    info: "AI 时代"
                }
			];

			resolve(this.themes);
		});
	}
}