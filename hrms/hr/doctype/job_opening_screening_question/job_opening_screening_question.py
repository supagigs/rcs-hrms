# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class JobOpeningScreeningQuestion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		description: DF.SmallText | None
		is_active: DF.Check
		is_mandatory: DF.Check
		max_length: DF.Int
		max_value: DF.Float
		min_length: DF.Int
		min_value: DF.Float
		options: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		question: DF.SmallText
		question_type: DF.Literal[
			"Short Text",
			"Long Text",
			"Number",
			"Currency",
			"Yes/No",
			"Single Select (Radio)",
			"Multiple Select",
			"Dropdown",
			"Date",
			"URL",
			"Email",
		]
	# end: auto-generated types

	pass
