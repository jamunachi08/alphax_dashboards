import frappe
from frappe.utils import getdate, add_days, nowdate

def _date_range(from_date=None, to_date=None):
    to_date = getdate(to_date) if to_date else getdate(nowdate())
    from_date = getdate(from_date) if from_date else add_days(to_date, -30)
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date

@frappe.whitelist()
def get_crm_summary(from_date=None, to_date=None, territory=None, owner=None):
    """CRM KPIs (safe defaults). Works even if some doctypes are missing."""
    from_date, to_date = _date_range(from_date, to_date)

    out = {
        "range": {"from_date": str(from_date), "to_date": str(to_date)},
        "kpis": {},
        "trend": [],
        "top_owners": [],
    }

    # Leads
    if frappe.db.exists("DocType", "Lead"):
        lead_filters = {"creation": ["between", [from_date, to_date]]}
        if territory and frappe.db.has_column("Lead", "territory"):
            lead_filters["territory"] = territory
        if owner:
            lead_filters["owner"] = owner
        out["kpis"]["leads_created"] = frappe.db.count("Lead", lead_filters)
        out["kpis"]["total_leads"] = frappe.db.count("Lead")

    # Opportunities
    if frappe.db.exists("DocType", "Opportunity"):
        opp_filters = {"creation": ["between", [from_date, to_date]]}
        if owner:
            opp_filters["owner"] = owner
        out["kpis"]["opportunities_created"] = frappe.db.count("Opportunity", opp_filters)

        out["kpis"]["open_opportunities"] = frappe.db.count("Opportunity", {"status": ["in", ["Open", "Open - In Progress", "Open - Not Contacted"]]})

        try:
            out["kpis"]["open_opp_value"] = float(frappe.db.sql("""
                select ifnull(sum(base_opportunity_amount),0)
                from `tabOpportunity`
                where status in ('Open','Open - In Progress','Open - Not Contacted')
            """)[0][0] or 0)
        except Exception:
            out["kpis"]["open_opp_value"] = 0.0

    # Quotations / Sales Orders (if ERPNext selling is installed)
    if frappe.db.exists("DocType", "Quotation"):
        out["kpis"]["quotations_created"] = frappe.db.count("Quotation", {"creation": ["between", [from_date, to_date]]})
        out["kpis"]["quotations_open"] = frappe.db.count("Quotation", {"status": ["in", ["Open", "Draft"]]})
    if frappe.db.exists("DocType", "Sales Order"):
        out["kpis"]["sales_orders_created"] = frappe.db.count("Sales Order", {"creation": ["between", [from_date, to_date]]})
        out["kpis"]["sales_orders_open"] = frappe.db.count("Sales Order", {"status": ["in", ["Draft", "To Deliver and Bill", "To Bill"]]})

    # Simple daily trend: leads created
    if frappe.db.exists("DocType", "Lead"):
        rows = frappe.db.sql("""
            select date(creation) as d, count(*) as c
            from `tabLead`
            where date(creation) between %s and %s
            group by date(creation)
            order by d
        """, [from_date, to_date], as_dict=True)
        out["trend"] = [{"x": str(r.d), "y": int(r.c)} for r in rows]

    # Top owners by created leads (last 30 days)
    if frappe.db.exists("DocType", "Lead"):
        rows = frappe.db.sql("""
            select owner, count(*) as c
            from `tabLead`
            where date(creation) between %s and %s
            group by owner
            order by c desc
            limit 10
        """, [from_date, to_date], as_dict=True)
        out["top_owners"] = [{"owner": r.owner, "count": int(r.c)} for r in rows]

    return out
