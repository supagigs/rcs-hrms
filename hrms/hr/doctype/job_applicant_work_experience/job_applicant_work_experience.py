# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class JobApplicantWorkExperience(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company_name: DF.Data
		currently_working: DF.Check
		description: DF.SmallText | None
		designation: DF.Data | None
		from_date: DF.Date
		location: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_date: DF.Date | None
	# end: auto-generated types

	pass
