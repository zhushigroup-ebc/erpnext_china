import frappe
from frappe.core.doctype.user.user import User

class CustomUser(User):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.block_module.block_module import BlockModule
		from frappe.core.doctype.defaultvalue.defaultvalue import DefaultValue
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.core.doctype.user_email.user_email import UserEmail
		from frappe.core.doctype.user_social_login.user_social_login import UserSocialLogin
		from frappe.types import DF

		allowed_in_mentions: DF.Check
		api_key: DF.Data | None
		api_secret: DF.Password | None
		banner_image: DF.AttachImage | None
		bio: DF.SmallText | None
		birth_date: DF.Date | None
		block_modules: DF.Table[BlockModule]
		bulk_actions: DF.Check
		bypass_restrict_ip_check_if_2fa_enabled: DF.Check
		dashboard: DF.Check
		default_app: DF.Literal[None]
		default_workspace: DF.Link | None
		defaults: DF.Table[DefaultValue]
		desk_theme: DF.Literal["Light", "Dark", "Automatic",'AIEra']
		document_follow_frequency: DF.Literal["Hourly", "Daily", "Weekly"]
		document_follow_notify: DF.Check
		email: DF.Data
		email_signature: DF.SmallText | None
		enabled: DF.Check
		first_name: DF.Data
		follow_assigned_documents: DF.Check
		follow_commented_documents: DF.Check
		follow_created_documents: DF.Check
		follow_liked_documents: DF.Check
		follow_shared_documents: DF.Check
		form_sidebar: DF.Check
		full_name: DF.Data | None
		gender: DF.Link | None
		home_settings: DF.Code | None
		interest: DF.SmallText | None
		language: DF.Link | None
		last_active: DF.Datetime | None
		last_ip: DF.ReadOnly | None
		last_known_versions: DF.Text | None
		last_login: DF.ReadOnly | None
		last_name: DF.Data | None
		last_password_reset_date: DF.Date | None
		last_reset_password_key_generated_on: DF.Datetime | None
		list_sidebar: DF.Check
		location: DF.Data | None
		login_after: DF.Int
		login_before: DF.Int
		logout_all_sessions: DF.Check
		middle_name: DF.Data | None
		mobile_no: DF.Data | None
		module_profile: DF.Link | None
		mute_sounds: DF.Check
		new_password: DF.Password | None
		notifications: DF.Check
		onboarding_status: DF.SmallText | None
		phone: DF.Data | None
		redirect_url: DF.SmallText | None
		reset_password_key: DF.Data | None
		restrict_ip: DF.SmallText | None
		role_profile_name: DF.Link | None
		roles: DF.Table[HasRole]
		search_bar: DF.Check
		send_me_a_copy: DF.Check
		send_welcome_email: DF.Check
		simultaneous_sessions: DF.Int
		social_logins: DF.Table[UserSocialLogin]
		thread_notify: DF.Check
		time_zone: DF.Autocomplete | None
		timeline: DF.Check
		unsubscribed: DF.Check
		user_emails: DF.Table[UserEmail]
		user_image: DF.AttachImage | None
		user_type: DF.Link | None
		username: DF.Data | None
		view_switcher: DF.Check