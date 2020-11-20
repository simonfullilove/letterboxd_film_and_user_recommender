import urllib.request, urllib.parse, urllib.error
import re
import math

def get_users_scores(user, score):
    """
    Gets all films that a certain user has given a certain rating on letterboxd.com

    :param user: (string) letterboxd username whose ratings you want to get.
    :param score: (string) the rating you want to get films for, e.g. '4' or '4.5'.
    :return: array of films that the user has given the specified score
    """
    found_films = []
    score_dict = {
        '0': 'none',
        '0.5': '%C2%BD',
        '1': '1',
        '1.5': '1%C2%BD',
        '2': '2',
        '2.5': '2%C2%BD',
        '3': '3',
        '3.5': '3%C2%BD',
        '4': '4',
        '4.5': '4%C2%BD',
        '5': '5'
    }
    print('Searching for %s\'s %s star movies...' % (user, score))
    score = score_dict[score]
    webpage_number = 0
    while True:
        new_films = []
        webpage_number += 1
        ratings_page = urllib.request.urlopen('https://letterboxd.com/%s/films/ratings/rated/%s/by/date/page/%d/' % (user, score, webpage_number))
        for line in ratings_page:
            for film in re.findall(r'data-film-slug="/film/(.+?)/"', line.decode()):
                new_films.append(film)
        if new_films == []:
            print('Done!')
            break
        else:
            found_films.extend(new_films)
    return found_films

def get_similar_raters(films, myscore, lowerbound, similar_user_dict):
    """
    Given a list of films and an original user's score and an acceptable lower boundary, this returns a
    dictionary of users who also liked these movies and a score for each user, the higher the more similar they are

    :param films: (list) list of films to check for high ratings
    :param myscore: (int) our original user's rating for the each film in the list of films e.g. '5' or '4.5'
    :param lowerbound: (int) the lowest rating a user can have given to be considered a similar user e.g. '4' or '3.5'
    :param similar_user_dict: (dict) a dictionary that will be updated with scores for users who also liked these films
    :return: a dictionary where keys are users and values are the user's score based on number of liked films etc.
    """
    def similarity_scorer(myscore, theirscore, avgrating, ratingcount):
        """
        Arbitrary algorithm to give a score based on our original user's rating, the similar user's rating, their
        difference from the average rating, and the obscurity of the film based on its rating count

        :param myscore: (float) original user's score
        :param theirscore: (float) similar user's score
        :param avgrating: (float) the film's average rating
        :param ratingcount: (int) the number of ratings the film has overall
        :return: (float) returns a float score
        """
        # return (((6 * myscore + 4 * theirscore) - 2 * avgrating) ** 2) * 100 / math.sqrt(ratingcount)
        return ((4 * myscore + 6 * theirscore) - 10 * avgrating) * (100 / math.sqrt(ratingcount))

    str_score_dict = {
        0.0: '0',
        0.5: '0.5',
        1.0: '1',
        1.5: '1.5',
        2.0: '2',
        2.5: '2.5',
        3.0: '3',
        3.5: '3.5',
        4.0: '4',
        4.5: '4.5',
        5.0: '5'
    }

    totalfilms = len(films)
    for film in films:
        webpage_number = 0
        main_page = urllib.request.urlopen('https://letterboxd.com/film/' + film + '/')
        main_page = str(list(main_page))
        clean_title = re.findall('data-film-name="(.+?)"', main_page)[0]
        try:
            avgrating = float(re.findall('"ratingValue":(.+?),"description"', main_page)[0])
        except:
            avgrating = 3
        try:
            ratingcount = int(re.findall('"ratingCount":(.+?),"worstRating"', main_page)[0])
        except:
            ratingcount = 30

        print('Checking high ratings for "%s"...' % clean_title)

        while True:
            webpage_number += 1
            print('Checking page %d...' % webpage_number)
            ratings_page = str(list(urllib.request.urlopen('https://letterboxd.com/film/%s/ratings/page/%d/' % (film, webpage_number))))
            found_something = False
            x = 5.0
            while x >= lowerbound:
                ratings_block = re.findall('<h2><span class="rating rating-large rated-large-' + str(int(x*2)) + '">(.+?)</ul>', ratings_page)
                if ratings_block:
                    found_something = True
                    for user in re.findall('href="/(.+?)/"', ratings_block[0]):
                        scoretoadd = similarity_scorer(myscore, x, avgrating, ratingcount)
                        similar_user_dict[user] = similar_user_dict.get(user, 0) + scoretoadd
                x -= 0.5
            if (found_something == False) and (x < lowerbound):
                totalfilms -= 1
                print('"%s" done! %d %s/5 film(s) remaining. \n' % (clean_title, totalfilms, str_score_dict[myscore]))
                break
    return similar_user_dict

def sort_dictionary_into_list(dict, descending=True, sort_by_values=True):
    """
    Takes a dictionary and returns a sorted list, sorted by either keys or values, in ascending or descending order.

    :param dict: (dict) dictionary to be sorted
    :param descending: (bool: default = True) whether to sort in descending order
    :param swap_keys_values: (bool: default = True) whether to sort by values. If false, sorts by keys instead
    :return: (list) sorted list
    """
    if sort_by_values:
        res = [(v,k) for k,v in iter(dict.items())]
        res.sort(reverse=descending)
        res = [(v,k) for k,v in res]
    else:
        res = [(k,v) for k,v in iter(dict.items())]
        res.sort(reverse=descending)
    return res

def get_top_good_users(user_list, num_of_results):
    """
    Takes a sorted list of tuples where user_list[n][0]=username and user_list[n][0]=userscore, and returns a maximum
    of num_of_results of the top users if they are deemed good users based on certain criteria such as the % of films
    they give 5/5 on letterboxd.com.

    :param user_list: (list) desc sorted list of users and scores - user_list[n][0]=username and user_list[n][0]=userscore
    :param num_of_results: (int) max number of good users to get before returning
    :return: (list) list of good users in descending order of score
    """

    res = []
    for user, score in user_list:
        new_entry = ('https://letterboxd.com/%s' % user, '%d' % score)
        print('Checking %s\'s profile... ' % user)
        ratings_page = urllib.request.urlopen('https://letterboxd.com/%s/' % user)
        ratings_str = str(list(ratings_page))
        try:
            fives_percentage = int(re.findall(r'/films/ratings/rated/5/by/date/".+?\((.+?)%\)', ratings_str)[0])
        except:
            fives_percentage = 0
        if fives_percentage <= 15:
            print('They\'re in!')
            res.append(new_entry)
            if len(res) == num_of_results:
                print('Lads, we have our top %s!:' % str(num_of_results))
                break
        else:
            print('This person doesn\'t know how to rate! They\'re out!')
    return res

def get_film_recommendations(similar_users, my_profile, num_of_recs):
    """
    Returns a list of max len num_of_recs containing list of films rated highly by users in similar users that are
    not marked as seen on my_profile, sorted in order of a score calculated by ratings given by users

    :param similar_users: (list) list where list[n][0] is a user's url on letterboxd.com
    :param my_profile: (str) the username of the person for whom we are checking similar users/unseen recommendations
    :param num_of_recs: (int) the max number of recommendations to return per returned list
    :return: (tuple) tuple containing three lists of tuples where list[n][0] = unseen film and list[n][1] = number of
    users who rated it highly sorted by the number of users. first list is all recommended films, second is more obscure
    films only, and third is most obscure, calculated by number of ratings
    """

    all_found_films = {}
    recommended_films = []
    obscure_recommended_films = []
    really_obscure_reommended_films = []

    for result in similar_users:
        username = re.findall('https://letterboxd.com/(.+)', result[0])[0]
        found_five_stars = get_users_scores(username, '5')
        for film in found_five_stars:
            all_found_films[film] = all_found_films.get(film, 0) + 2
        found_fourpointfive_stars = get_users_scores(username, '4.5')
        for film in found_fourpointfive_stars:
            all_found_films[film] = all_found_films.get(film, 0) + 1.5
        found_four_stars = get_users_scores(username, '4')
        for film in found_four_stars:
            all_found_films[film] = all_found_films.get(film, 0) + 1

    all_found_films = sort_dictionary_into_list(all_found_films)

    for film in all_found_films:
        ouractivity = urllib.request.urlopen('https://letterboxd.com/%s/film/%s/activity/' % (my_profile, film[0]))
        activity_str = str(list(ouractivity))
        if len(re.findall('"activity-summary"', activity_str)) == 0:
            recommended_films.append('https://letterboxd.com/film/%s: %d' % (film[0], film[1]))
            main_page = urllib.request.urlopen('https://letterboxd.com/film/%s/' % film[0])
            main_page = str(list(main_page))
            try:
                ratingcount = int(re.findall('"ratingCount":(.+?),"worstRating"', main_page)[0])
            except:
                ratingcount = 0
            if 1000 <= ratingcount < 10000:
                obscure_recommended_films.append('https://letterboxd.com/film/%s: %d' % (film[0], film[1]))
            if ratingcount < 1000:
                really_obscure_reommended_films.append('https://letterboxd.com/film/%s: %d' % (film[0], film[1]))
        if len(recommended_films) == num_of_recs:
            break
    return (recommended_films, obscure_recommended_films, really_obscure_reommended_films)

########################################################################################################################

myprofile = 'tsar'

favourite_films = {
    '5': get_users_scores(myprofile, '5'),
    '4.5': get_users_scores(myprofile, '4.5'),
    '4': get_users_scores(myprofile, '4')
}

# total_films = sum([len(favourite_films[rating]) for rating in favourite_films])
# print('Total films to check = %s' % total_films)

fellow_raters = {}
for rating in favourite_films:
    fellow_raters = get_similar_raters(favourite_films[rating], float(rating), 4, fellow_raters)
fellow_raters_sorted = sort_dictionary_into_list(fellow_raters)

top20 = get_top_good_users(fellow_raters_sorted, 20)
for result in top20:
    print(result[0],':', result[1])

recommended_films, obscure_recommended_films, really_obscure_reommended_films = get_film_recommendations(top20, myprofile, 50)

print('Recommended Films:')
for filmandscore in recommended_films:
    print(filmandscore)

print('Kinda Obscure Recommended Films:')
for filmandscore in obscure_recommended_films:
    print(filmandscore)

print('Really Obscure Recommended Films:')
for filmandscore in really_obscure_reommended_films:
    print(filmandscore)