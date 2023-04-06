""" Defined a class for adding all the helper methods"""
class StringProcessor:
    
    def __init__(self):
        pass

    # This method will return the substring between two characters
    def getSubstringBetweenTwoChars(self, ch1,ch2,s):
        if s.find(ch1) != -1 and s.find(ch2) != -1:
            return s[s.find(ch1)+1:s.find(ch2)]
        else:
            return s