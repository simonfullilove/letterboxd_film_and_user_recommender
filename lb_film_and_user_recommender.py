import urllib.request, urllib.parse, urllib.error
import http
import re
import math

def webpage_to_string(url):
    """
    Returns a string of the raw HTML for an entire web page.

    :param url: (string or HTTPResponse object') The URL of the website as a string, or an HTTPResponse object (part of
    the http library) that has been requested before being passed as an argument. This function handles either.
    :return: (string) A string of the raw HTML for the URL provided.
    """
    if isinstance(url, str):
        return str(list(urllib.request.urlopen(url)))
    elif isinstance(url, http.client.HTTPResponse):
        return str(list(url))
    else:
        return 'Error: URL provided is not a string or an HTTPResponse object'

def get_users_scores(user, score):
    """
    Gets all films that a certain user has given a certain rating on letterboxd.com

    :param user: (string) letterboxd username whose ratings you want to get.
    :param score: (string) the rating you want to get films for, e.g. '4' or '4.5'.
    :return: (list) a list of films that the user has given the specified score
    """
    found_films = []
    score_dict_for_url = {
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
    print(f'Searching for {user}\'s {score} star movies...')
    score_for_url = score_dict_for_url[score]
    ratings_page = f'https://letterboxd.com/{user}/films/ratings/rated/{score_for_url}/by/date/page/'
    webpage_number = 0
    while True:
        new_films = []
        webpage_number += 1
        ratings_page_numbered = urllib.request.urlopen(f'{ratings_page}{webpage_number}')
        for line in ratings_page_numbered:
            new_films += re.findall(r'data-film-slug="/film/(.+?)/"', line.decode())
        if not new_films:
            print('Done!')
            break
        found_films.extend(new_films)
    return found_films

def similarity_scorer(my_score, their_score, avg_rating, rating_count):
    """
    Arbitrary algorithm to give a score based on our original user's rating, the similar user's rating, their
    difference from the average rating, and the obscurity of the film based on its rating count

    The algorithm is designed as follows:
    1. Calculates the difference between the average score for a film and the combination of our rating and the
    similar user's rating (weighted to make their rating slightly more important). The higher the difference, the
    more unusual it is for us to like this film, resulting in a higher score.
    2. Takes this difference and multiplies it by 100 over the square root of the number of ratings the film has.
    This gives us a score that will be very high if the film has very few ratings (because the film is therefore
    obscure and it is unusual for us to both have seen it) and will be very low if a film has lots of ratings.

    :param my_score: (float) original user's score
    :param their_score: (float) similar user's score
    :param avg_rating: (float) the film's average rating
    :param rating_count: (int) the number of ratings the film has overall
    :return: (float) returns a float score
    """
    return (4 * my_score + 6 * their_score - 10 * avg_rating) * 100 / math.sqrt(rating_count)

def update_similar_raters_dict(films, my_score, lower_bound, similar_user_dict):
    """
    Given a list of films and an original user's score and an acceptable lower boundary, this function returns either an
    updated or newly populated dictionary containing users who also liked the movies in the 'films' list, and a
    similarity score for each. The higher their score, the more similar they are to us.

    :param films: (list) list of films to check for high ratings
    :param my_score: (int) our original user's rating for the each film in the list of films e.g. '5' or '4.5'
    :param lower_bound: (int or float) the lowest rating a user can have given to be considered a similar user e.g. '4'
    or '3.5'
    :param similar_user_dict: (dict) a dictionary that will be updated with scores for users who also liked these films
    :return: (dict) a dictionary where keys are users and values are the user's score based on number of liked films etc.
    """
    updated_dict = similar_user_dict.copy()
    total_films = len(films)
    for film in films:
        webpage_number = 0
        main_page = webpage_to_string(f'https://letterboxd.com/film/{film}/')
        clean_title = re.findall('data-film-name="(.+?)"', main_page)[0]
        avg_rating = re.findall('"ratingValue":(.+?),"description"', main_page)
        if avg_rating:
            avg_rating = float(avg_rating[0])
        else:
            avg_rating = 3
        ratingcount = re.findall('"ratingCount":(.+?),"worstRating"', main_page)
        if ratingcount:
            ratingcount = int(ratingcount[0])
        else:
            ratingcount = 30

        print(f'Checking high ratings for "{clean_title}"...')

        while True:
            webpage_number += 1
            print(f'Checking page {webpage_number}...')
            ratings_page = webpage_to_string(f'https://letterboxd.com/film/{film}/ratings/page/{webpage_number}/')
            found_something = False
            rating_to_find = 5.0
            while rating_to_find >= lower_bound:
                ratings_block = re.findall(
                    '<h2><span class="rating rating-large rated-large-' + str(int(rating_to_find * 2)) + '">(.+?)</ul>',
                    ratings_page)
                if ratings_block:
                    found_something = True
                    for user in re.findall('href="/(.+?)/"', ratings_block[0]):
                        score_to_add = similarity_scorer(my_score, rating_to_find, avg_rating, ratingcount)
                        updated_dict[user] = updated_dict.get(user, 0) + score_to_add
                rating_to_find -= 0.5
            if (not found_something) and (rating_to_find < lower_bound):
                total_films -= 1
                print(f'"{clean_title}" done! {total_films} {my_score:g}/5 film(s) remaining. \n')
                break
    return updated_dict

def get_top_good_users(user_list, num_of_results):
    """
    Takes a sorted list of tuples where user_list[n][0]=username and user_list[n][0]=userscore, and returns a maximum
    of num_of_results of the top users if they are deemed good users based on certain criteria such as the % of films
    they give 5/5 on letterboxd.com.

    :param user_list: (list) desc sorted list of users and scores - user_list[n][0]=username and
    user_list[n][1]=userscore
    :param num_of_results: (int) max number of good users to get before returning
    :return: (list) list of good users in descending order of score
    """

    res = []
    for user, score in user_list:
        new_entry = (f'https://letterboxd.com/{user}', f'{score}')
        print(f'Checking {user}\'s profile... ')
        ratings_str = webpage_to_string(f'https://letterboxd.com/{user}')
        fives_percentage = re.findall(r'/films/ratings/rated/5/by/date/".+?\((.+?)%\)', ratings_str)
        if fives_percentage:
            fives_percentage = int(fives_percentage[0])
        else:
            fives_percentage = 0
        if fives_percentage <= 15:
            print('They\'re in!')
            res.append(new_entry)
            if len(res) == num_of_results:
                print(f'Lads, we have our top {num_of_results}!:')
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
    really_obscure_recommended_films = []

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

    all_found_films = sorted(all_found_films.items(), key=lambda x: x[1], reverse=True)

    for film in all_found_films:
        activity_str = webpage_to_string(f'https://letterboxd.com/{my_profile}/film/{film[0]}/activity/')
        if not re.findall('"activity-summary"', activity_str):
            if len(recommended_films) < num_of_recs:
                recommended_films.append(f'https://letterboxd.com/film/{films[0]} : {film[1]}')
            main_page = webpage_to_string(f'https://letterboxd.com/film/{film[0]}/')
            ratingcount = re.findall('"ratingCount":(.+?),"worstRating"', main_page)
            if ratingcount:
                ratingcount = int(ratingcount[0])
            else:
                ratingcount = 0
            if (1000 <= ratingcount < 10000) and (len(obscure_recommended_films) < num_of_recs):
                obscure_recommended_films.append(f'https://letterboxd.com/film/{films[0]} : {film[1]}')
            if (ratingcount < 1000) and (len(really_obscure_recommended_films) < num_of_recs):
                really_obscure_recommended_films.append(f'https://letterboxd.com/film/{films[0]} : {film[1]}')
        if (len(recommended_films) and len(obscure_recommended_films) and len(
                really_obscure_recommended_films)) == num_of_recs:
            break
    return recommended_films, obscure_recommended_films, really_obscure_recommended_films

########################################################################################################################

myprofile = 'tsar'

favourite_films = {
    '5': get_users_scores(myprofile, '5'),
    '4.5': get_users_scores(myprofile, '4.5'),
    '4': get_users_scores(myprofile, '4')
}

similar_raters = {}
for rating in favourite_films:
    similar_raters = update_similar_raters_dict(favourite_films[rating], float(rating), 4, similar_raters)
similar_raters_sorted = sorted(similar_raters.items(), key=lambda x:x[1], reverse=True)

top20 = get_top_good_users(similar_raters_sorted, 20)

for result in top20:
    print(result[0], ':', result[1])

recommended_films, obscure_recommended_films, really_obscure_recommended_films = get_film_recommendations(top20,
                                                                                                          myprofile, 5)

print('Recommended Films:')
for film_and_score in recommended_films:
    print(film_and_score)

print('Kinda Obscure Recommended Films:')
for film_and_score in obscure_recommended_films:
    print(film_and_score)

print('Really Obscure Recommended Films:')
for film_and_score in really_obscure_recommended_films:
    print(film_and_score)