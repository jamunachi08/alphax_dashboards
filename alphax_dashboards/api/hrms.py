import frappe
from frappe.utils import getdate, add_days, nowdate

def _date_range(from_date=None, to_date=None):
    to_date = getdate(to_date) if to_date else getdate(nowdate())
    from_date = getdate(from_date) if from_date else add_days(to_date, -30)
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date

def _exists(dt):
    return frappe.db.exists("DocType", dt)

@frappe.whitelist()
def get_hrms_summary(from_date=None, to_date=None, company=None, branch=None, department=None):
    """HRMS management/self-service neutral KPIs."""
    from_date, to_date = _date_range(from_date, to_date)

    out = {
        "range": {"from_date": str(from_date), "to_date": str(to_date)},
        "filters": {"company": company, "branch": branch, "department": department},
        "kpis": {},
        "attendance": {"present": 0, "absent": 0, "on_leave": 0},
        "trend": [],
    }

    if not _exists("Employee"):
        out["error"] = "Employee doctype not found (HRMS/ERPNext not installed?)"
        return out

    emp_filters = {"status": "Active"}
    if company and frappe.db.has_column("Employee", "company"):
        emp_filters["company"] = company
    if branch and frappe.db.has_column("Employee", "branch"):
        emp_filters["branch"] = branch
    if department and frappe.db.has_column("Employee", "department"):
        emp_filters["department"] = department

    out["kpis"]["active_employees"] = frappe.db.count("Employee", emp_filters)

    # hires in range
    if frappe.db.has_column("Employee", "date_of_joining"):
        f = dict(emp_filters)
        f["date_of_joining"] = ["between", [from_date, to_date]]
        out["kpis"]["new_hires"] = frappe.db.count("Employee", f)

    # exits in range (relieving_date is in ERPNext)
    if frappe.db.has_column("Employee", "relieving_date"):
        f = dict(emp_filters)
        f.pop("status", None)  # relieving may be for left employees too
        if company and frappe.db.has_column("Employee", "company"):
            f["company"] = company
        if branch and frappe.db.has_column("Employee", "branch"):
            f["branch"] = branch
        if department and frappe.db.has_column("Employee", "department"):
            f["department"] = department
        f["relieving_date"] = ["between", [from_date, to_date]]
        out["kpis"]["exits"] = frappe.db.count("Employee", f)

    # attendance summary
    if _exists("Attendance"):
        cond = ["date(attendance_date) between %s and %s"]
        vals = [from_date, to_date]
        if company and frappe.db.has_column("Attendance", "company"):
            cond.append("company=%s"); vals.append(company)
        if branch and frappe.db.has_column("Attendance", "branch"):
            cond.append("branch=%s"); vals.append(branch)

        rows = frappe.db.sql(f"""
            select status, count(*) as c
            from `tabAttendance`
            where {' and '.join(cond)}
            group by status
        """, vals, as_dict=True)
        for r in rows:
            s = (r.status or "").lower()
            if "present" in s: out["attendance"]["present"] += int(r.c)
            elif "absent" in s: out["attendance"]["absent"] += int(r.c)
            elif "leave" in s: out["attendance"]["on_leave"] += int(r.c)

    # trend: hires per day
    if frappe.db.has_column("Employee", "date_of_joining"):
        rows = frappe.db.sql("""
            select date(date_of_joining) as d, count(*) as c
            from `tabEmployee`
            where date(date_of_joining) between %s and %s
            group by date(date_of_joining)
            order by d
        """, [from_date, to_date], as_dict=True)
        out["trend"] = [{"x": str(r.d), "y": int(r.c)} for r in rows]

    # leave applications
    if _exists("Leave Application") and frappe.db.has_column("Leave Application", "from_date"):
        cond = ["docstatus=1", "date(from_date) between %s and %s"]
        vals = [from_date, to_date]
        if company and frappe.db.has_column("Leave Application", "company"):
            cond.append("company=%s"); vals.append(company)
        out["kpis"]["approved_leaves"] = int(frappe.db.sql(f"select count(*) from `tabLeave Application` where {' and '.join(cond)}", vals)[0][0] or 0)

    return out
