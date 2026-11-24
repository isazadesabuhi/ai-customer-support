SUPPORT_AGENT_GROUP = "Support Agent"
SUPPORT_MANAGER_GROUP = "Support Manager"
SUPPORT_GROUPS = (SUPPORT_AGENT_GROUP, SUPPORT_MANAGER_GROUP)

VIEW_CONVERSATION = "support.view_conversation"
ADD_CONVERSATION = "support.add_conversation"
VIEW_MESSAGE = "support.view_message"
ADD_MESSAGE = "support.add_message"
SUPPORT_PERMISSIONS = (VIEW_CONVERSATION, ADD_CONVERSATION, VIEW_MESSAGE, ADD_MESSAGE)


def support_role(user):
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "superuser"

    groups = set(
        user.groups.filter(name__in=SUPPORT_GROUPS).values_list("name", flat=True)
    )
    if SUPPORT_MANAGER_GROUP in groups:
        return "support_manager"
    if SUPPORT_AGENT_GROUP in groups:
        return "support_agent"
    return None
