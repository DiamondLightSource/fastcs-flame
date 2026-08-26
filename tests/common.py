def lists_equal(list1, list2):
    """
    Checks if two lists are equal
    """
    if len(list1) != len(list2):
        return False
    return all(list1[i] == list2[i] for i in range(len(list1)))
