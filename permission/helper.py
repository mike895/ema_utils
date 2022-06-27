from em_member.em_member.doctype.ema_permission.ema_permission import EmaPermission
from typing import Union
import frappe
def remove_else(container, child):
    return list(set(container) - set(child))

def is_role_allowed(required_role, my_roles, throw=False):
    if(required_role not in my_roles):
        if(throw): raise Exception("You don't have permission for this document!")
        return False
    return True



def is_allowed(permission:Union[EmaPermission, str], branchs:list, throw=False, all_match=True):
    if(permission == "admin"):
        return True
    if(permission.all_branch != 1):   # all_regions = all_branch and region_item = branch and regions = branchs
        allowed_branchs = [i.branch for i in permission.branch]
        if(not (all if(all_match) else any)(branch in allowed_branchs for branch in branchs)):
            if(throw): raise Exception(f"You don't have permission for branch {', '.join(remove_else(branchs, allowed_branchs))}.")
            return False            
    return True
    
