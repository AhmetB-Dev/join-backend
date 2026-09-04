from django.core.cache import cache


TASK_LIST_CACHE_KEY_VERSION = "v1"


def task_list_cache_key(user_id):
    return f"join:tasks:{TASK_LIST_CACHE_KEY_VERSION}:user:{user_id}"


def invalidate_task_list_cache(user_id):
    cache.delete(task_list_cache_key(user_id))
