import hdhp
import json
import numpy as np
import os
import timeit
from datetime import datetime
import random
import operator



def jsonFileToEvents (targetFile):

    start = timeit.default_timer()
    names_to_ids = maps_authors_to_ids(targetFile)

    events = list ()
    json_data = json.load(open(targetFile))
    times = {}

    for identifier in json_data:
        paper = json_data.get(identifier)
        times[identifier] = paper["time"]
    
    sorted_times = sorted(times.items(), key=operator.itemgetter(1))

    for item in sorted_times:
        identifier = item[0]
        paper = json_data.get(identifier)
   
        authors_vocabs = ''
        
        for citation in paper["citations"]:
            authors = citation["author"]

            for author in authors:
                authors_vocabs += author.strip() + ' '
        # for author in paper["author"]:
        #     splits = author.split(',')
        #     new_format = splits[1].strip() + ' ' + splits[0].strip()
        #     authors_vocabs += new_format + ' '

        vocabularies = {"docs": paper["abstract"], "auths": authors_vocabs.strip()}


        event = (paper["time"], vocabularies, paper["author_ids"], [])
        events.append(event)

    print("Number of events: " + str(len(events)))
    print("Execution Time: " + str(timeit.default_timer() - start))
    return events

def find_first_date (targetFile):

    json_data = json.load(open(targetFile))
    first_date = datetime.now()

    for identifier in json_data:
        paper = json_data.get(identifier)
        paper_time = datetime.strptime(paper["date"][0], '%Y-%m-%d')

        if paper_time < first_date:
            first_date = paper_time

    print(str(first_date))


def num_unique_authors (targetFile):

    json_data = json.load(open(targetFile))
    unique_authors = []

    for identifier in json_data:
        paper = json_data.get(identifier)
        for author in paper["author"]:
            unique_authors.append(author.strip())

    print("Number of all authors: " + str(len(unique_authors)))
    print("Number of unique authors: " + str(len(set(unique_authors))))


def maps_authors_to_ids(targetFile):

    json_data = json.load(open(targetFile))
    new_file = "/NL/publications-corpus/work/new_CS_arXiv_real_data.json"
    base_time = datetime.strptime('1996-06-03', '%Y-%m-%d')
    counter = 0;
    names_to_ids = {}
    new_json_data = {}

    for identifier in json_data:
        paper = json_data.get(identifier)

        authors = paper["author"]
        for author in authors:
            if author.strip() not in names_to_ids:
                counter += 1
                names_to_ids[author.strip()] = counter


    for identifier in json_data:
        paper = json_data.get(identifier)

        authors = paper["author"]
        ids = []
        for author in authors:
            ids.append(names_to_ids.get(author.strip()))
        paper['author_ids'] = ids

        paper_time = datetime.strptime(paper["date"][0], '%Y-%m-%d')
        time_diff = paper_time - base_time
        time = time_diff.total_seconds()/(3600*24) + random.uniform(0, 1)
        paper['time'] = time
        new_json_data[identifier] = paper

    with open(new_file, 'w') as output_file:
        json.dump(new_json_data, output_file, indent=1)
    print("Number of unique ids: " + str(len(names_to_ids)))
    return names_to_ids


def infer (rawEvents, indices, use_cousers=False):

    start = timeit.default_timer()

    types = ["docs", "auths"]
    # priors to control the time dynamics of the events
    alpha_0 = (4.0, 0.5) # prior for excitation
    mu_0 = (8, 0.25) # prior for base intensity
    o = 3.5 # decay kernel

    num_patterns = 10
    num_users = 64442 # Number of unique authors

    # # Inference
    types = [types[i] for i in indices]

    events = list ()

    if use_cousers:
        for event in rawEvents:
            events.append ((event[0], {t: event[1][t] for t in types}, event[2], event[3]))
    else:
        for event in rawEvents:
            events.append ((event[0], {t: event[1][t] for t in types}, [event[2][0]], event[3]))

    particle, norms = hdhp.infer(events,
                                 num_users,
                                 types,
                                 alpha_0,
                                 mu_0,
                                 omega=o,
                                 beta=1, 
                                 threads=1, 
                                 num_particles=50, 
                                 keep_alpha_history=True,
                                 seed=512)

    print("Execution time of calling infer function: " + str(timeit.default_timer() - start))
    start = timeit.default_timer()

    inf_process = particle.to_process()
    print("Convert to process - time: " + str(timeit.default_timer() - start))

    return inf_process


def main ():

    real_data_file_path = "/NL/publications-corpus/work/new_CS_arXiv_real_data.json"

    events = jsonFileToEvents(real_data_file_path)
    number_of_events = 100
    print("Number of events: " + str(number_of_events))

    cases = {1: ([0], False),
             2: ([0,1], False),
             3: ([0,1], True)}

    for case in [1,2,3]:
        print "Case: {0}".format (case)
        indices, use_cousers = cases[case]
       
        print("Start inferring.....")
        infHDHP = infer(events[: number_of_events], indices, use_cousers)   
        print("End inferring...")
        clusters = infHDHP.show_annotated_events()
        with open("real_data_results/annotated_events_" + "Case: {0}".format (case) + "_" + str(number_of_events)+ ".txt", "w") as output_file:
            output_file.write(clusters)

        dist = infHDHP.show_pattern_content()
        with open("real_data_results/pattern_content_" + "Case: {0}".format (case) + "_" + str(number_of_events)+ ".txt", "w") as output_file:
            output_file.write(dist)
        print("show_pattern_content return: \n" + dist)

    
if __name__ == "__main__":
    main ()
