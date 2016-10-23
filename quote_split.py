def quote_split(s):
    final_s = []
    while len(s.split()) > 0:
        #print("s: {}".format(s))
        space_index = s.find(' ')
        squote_index = s.find("'")
        dquote_index = s.find('"')
        if space_index == squote_index and dquote_index == squote_index:
            final_s.append(s)
            s = "" 
        elif min([i for i in (space_index, squote_index, dquote_index) if i != -1]) == space_index:
            final_s.append(s.split()[0])
            s = ' '.join(s.split()[1:])
        elif min([i for i in (space_index, squote_index, dquote_index) if i != -1]) == squote_index:
            end_quote = s.find("'", squote_index + 1)
            final_s.append(s[squote_index + 1: end_quote])
            s = s[end_quote+1:]
        elif min([i for i in (space_index, squote_index, dquote_index) if i != -1]) == dquote_index:
            end_quote = s.find('"', dquote_index + 1)
            final_s.append(s[dquote_index + 1: end_quote])
            s = s[end_quote+1:]
    return final_s

example = 'This is a string with a "long, multiword \'quoted\' substring" for \'tests\''
