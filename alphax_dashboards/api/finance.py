import frappe
from frappe.utils import getdate, add_days, nowdate

def _date_range(from_date=None, to_date=None):
    to_date = getdate(to_date) if to_date else getdate(nowdate())
    from_date = getdate(from_date) if from_date else add_days(to_date, -30)
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date

def _sum_gl(root_type, from_date, to_date, company=None, cost_center=None):
    cond = ["gle.is_cancelled = 0", "date(gle.posting_date) between %s and %s", "acc.root_type = %s"]
    vals = [from_date, to_date, root_type]
    if company:
        cond.append("gle.company = %s")
        vals.append(company)
    if cost_center and frappe.db.has_column("GL Entry", "cost_center"):
        cond.append("gle.cost_center = %s")
        vals.append(cost_center)

    return float(frappe.db.sql(f"""
        select ifnull(sum(gle.debit - gle.credit), 0)
        from `tabGL Entry` gle
        inner join `tabAccount` acc on acc.name = gle.account
        where {' and '.join(cond)}
    """, vals)[0][0] or 0)

@frappe.whitelist()
def get_finance_summary(from_date=None, to_date=None, company=None, cost_center=None):
    """Finance summary computed from GL Entry + Account root_type (Income/Expense)."""
    from_date, to_date = _date_range(from_date, to_date)

    if not frappe.db.exists("DocType", "GL Entry"):
        return {"error": "GL Entry doctype not found (ERPNext not installed?)"}

    income = _sum_gl("Income", from_date, to_date, company, cost_center)
    expenses = _sum_gl("Expense", from_date, to_date, company, cost_center)
    profit = income - expenses

    top_exp = []
    try:
        cond = ["gle.is_cancelled = 0", "date(gle.posting_date) between %s and %s", "acc.root_type='Expense'"]
        vals = [from_date, to_date]
        if company:
            cond.append("gle.company = %s"); vals.append(company)
        if cost_center and frappe.db.has_column("GL Entry", "cost_center"):
            cond.append("gle.cost_center = %s"); vals.append(cost_center)

        rows = frappe.db.sql(f"""
            select gle.account, ifnull(sum(gle.debit - gle.credit), 0) as amount
            from `tabGL Entry` gle
            inner join `tabAccount` acc on acc.name = gle.account
            where {' and '.join(cond)}
            group by gle.account
            order by amount desc
            limit 10
        """, vals, as_dict=True)
        top_exp = [{"account": r.account, "amount": float(r.amount or 0)} for r in rows]
    except Exception:
        top_exp = []

    # daily profit trend (income-expense)
    trend = []
    try:
        rows = frappe.db.sql("""
            select d, 
                sum(case when root_type='Income' then amt else 0 end) as income,
                sum(case when root_type='Expense' then amt else 0 end) as expense
            from (
                select date(gle.posting_date) as d, acc.root_type, (gle.debit - gle.credit) as amt
                from `tabGL Entry` gle
                inner join `tabAccount` acc on acc.name = gle.account
                where gle.is_cancelled=0
                  and date(gle.posting_date) between %s and %s
                  and acc.root_type in ('Income','Expense')
                  { 'and gle.company=%s' if company else '' }
                  { 'and gle.cost_center=%s' if (cost_center and frappe.db.has_column('GL Entry','cost_center')) else '' }
            ) x
            group by d
            order by d
        """, [from_date, to_date] + ([company] if company else []) + ([cost_center] if (cost_center and frappe.db.has_column('GL Entry','cost_center')) else []), as_dict=True)
        for r in rows:
            trend.append({"x": str(r.d), "y": float((r.income or 0) - (r.expense or 0))})
    except Exception:
        trend = []

    return {
        "range": {"from_date": str(from_date), "to_date": str(to_date)},
        "filters": {"company": company, "cost_center": cost_center},
        "kpis": {
            "income": income,
            "expenses": expenses,
            "profit": profit
        },
        "trend": trend,
        "top_expenses": top_exp
    }
