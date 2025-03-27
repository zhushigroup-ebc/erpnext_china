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
                    name:"aiera",
                    label: __("AIEra"),
                    info: "AI"
                }
			];

			resolve(this.themes);
		});
	}
}