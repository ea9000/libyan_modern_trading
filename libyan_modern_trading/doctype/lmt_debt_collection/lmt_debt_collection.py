import frappe
from frappe.model.document import Document
from frappe import _

class LMTDebtCollection(Document):
    def validate(self):
        if self.action_type == "ايداع":
            self.calculate_commission()
            self.validate_receipt_range()
        elif self.action_type == "سحب":
            self.validate_draw_limit()

    def calculate_commission(self):
        """Calculates agent commission based on customer type and agent percentages"""
        if not self.customer:
            return

        # 1. Fetch Customer Type
        cust_type = frappe.db.get_value("Customer", self.customer, "lmt_cust_type")
        
        # 2. Fetch Agent (User) Percentages
        # We use the 'owner' (the agent who created the record)
        agent_data = frappe.db.get_value("User", self.owner, 
            ["lmt_percentage_1", "lmt_percentage_2"], as_dict=1)

        if not agent_data:
            return

        # 3. Apply Logic: Pharmacy (percentage_1) vs Company (percentage_2)
        if cust_type == "Pharmacy":
            self.agent_percentage = agent_data.lmt_percentage_1 or 0
        else:
            self.agent_percentage = agent_data.lmt_percentage_2 or 0

        # 4. Calculate Amount
        self.agent_commission = (self.amount * self.agent_percentage) / 100

    def validate_receipt_range(self):
        """Ensures the receipt number is within the agent's assigned booklet range"""
        if not self.receipt_no:
            return

        ranges = frappe.db.get_value("User", self.owner, 
            ["lmt_booklet_start", "lmt_booklet_end"], as_dict=1)

        if ranges and ranges.lmt_booklet_start and ranges.lmt_booklet_end:
            r_no = int(self.receipt_no)
            if not (ranges.lmt_booklet_start <= r_no <= ranges.lmt_booklet_end):
                frappe.throw(_("رقم الواصل {0} خارج النطاق المسموح لك ({1} - {2})").format(
                    self.receipt_no, ranges.lmt_booklet_start, ranges.lmt_booklet_end
                ))

    def validate_draw_limit(self):
        """Prevents agent from drawing more than their available credit"""
        # This is a placeholder for the credit limit logic
        # You can query the sum of percentages vs sum of previous draws here
        pass
