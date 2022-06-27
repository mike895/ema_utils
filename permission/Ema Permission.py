import frappe
import frappe.desk.form.load as load
import frappe.desk.form.save as save_
import frappe.desk.reportview as lister
from em_member.utils.permission import helper
from frappe.model.db_query import DatabaseQuery
from frappe import _
from frappe.desk.form.load import run_onload

class CustomDatabaseQuery(DatabaseQuery):
    def build_and_run(self):
        args = self.prepare_args()
        args.limit = self.add_limit()
        if args.conditions:
            args.conditions = "where " + args.conditions
        elif (self.branchs != "all"):
            args.conditions = "where "
        query = f"""select %(fields)s
            from %(tables)s
            %(conditions)s
            {f'''{"AND " if(self.conditions.__len__() > 0) else ""}NOT EXISTS(select 1 from `tabBranch` 
                    where `tabBranch`.`parent` = `tabEma Permission`.`name`
                                        AND  `tabBranch`.`branchs` NOT IN ({self.branchs}))''' if (self.branchs != "all") else ""}
            %(group_by)s
            %(order_by)s
            %(limit)s""" % args
        if self.return_query:
            return query
        else:
            return frappe.db.sql(query, as_dict=not self.as_list, debug=self.debug,
                update=self.update, ignore_ddl=self.ignore_ddl)

@frappe.whitelist(allow_guest=True)
def getlist(permission): 
    allowed_branchs =  "all" if((permission == "admin") or (permission.all_branch == 1)) else ", ".join([f"'{i.branch}'" for i in permission.branchs]) 
    args = lister.get_form_params()
    dbq = CustomDatabaseQuery("Ema Permission")
    dbq.branchs = allowed_branchs
    result = (lambda doctype, *args, **kwargs:  dbq.execute(join="inner join",
    group_by="`tabEma Permission`.`name`",
    with_childnames=True
    ))(**args)
    return result

def getcount(permission):
    allowed_branchs =  "all" if((permission == "admin") or (permission.all_branch == 1)) else ", ".join([f"'{i.branch}'" for i in permission.branch]) 
    args = lister.get_form_params()
    distinct = 'distinct ' if args.distinct=='true' else ''
    args.fields = [f"count({distinct}`tabEma Permission`.name) as total_count"]
    dbq = CustomDatabaseQuery("Ema Permission")
    dbq.branchs = allowed_branchs
    result = (lambda doctype, *args, **kwargs:  dbq.execute(*args, **kwargs))(**args)
    return result[0].get("total_count")

@frappe.whitelist(allow_guest=True)
def getdoc(name, permission):
    doctype = "Ema Permission"

    if not (doctype and name):
        raise Exception('doctype and name required!')
    if not name:
        name = doctype
    
    if not frappe.db.exists(doctype, name):
        return []

    try:
        doc = frappe.get_doc(doctype, name)
        helper.is_allowed(permission, [i.branch for i in doc.branch], throw=True)
        load.run_onload(doc)
        if not doc.has_permission("read"):
            frappe.flags.error_message = _('Insufficient Permission for {0}').format(frappe.bold(doctype + ' ' + name))
            raise frappe.PermissionError(("read", doctype, name))

        doc.apply_fieldlevel_read_permissions()

        # add file list
        doc.add_viewed()
        load.get_docinfo(doc)

    except Exception:
        frappe.errprint(frappe.utils.get_traceback())
        raise

    doc.add_seen()

    frappe.response.docs.append(doc)

@frappe.whitelist()
def save(permission, doc, action):  # all_regions = all_branch and region_item = branch and regions = branchs
    """save / submit / update doclist"""
    try:
        if((permission != "admin") and (doc["user"] == permission.user)):
            raise Exception(_("You can't set your own permission!"))
        if((permission != "admin") and (doc['all_branch'] == 1 and permission.all_branch != 1)):
            raise Exception(_("You can't set All Branchs if you don't have All Branchs permission."))
        helper.is_allowed(permission, [i['branch'] for i in (doc.get('branch') or []) ], throw=True)
        doc = frappe.get_doc(doc)
        save_.set_local_name(doc)
        # action
        doc.docstatus = {"Save":0, "Submit": 1, "Update": 1, "Cancel": 2}[action]
        if doc.docstatus==1:
            doc.submit()
        else:
            doc.save()

        # update recent documents
        run_onload(doc)
        save_.send_updated_docs(doc)

        frappe.msgprint(frappe._("Saved"), indicator='green', alert=True)
    except Exception:
        frappe.errprint(frappe.utils.get_traceback())
        raise
