"""
Created on 1.2.2016

@author: mohamed.megahed
"""

import json
import glob
import datetime
import math

from dataStructure.Candidate import Candidate
from dataStructure.ProtectedAttribute import ProtectedAttribute
import os

from utils.readWriteRankings import *
from tables.flavor import identifier_map
from utils.normalizeQualifications import normalizeQualifications


class XINGDataSetSimulator(object):
    """
    reads profiles collected from Xing on certain job description queries
    profiles are available in JSON format and are read into two arrays of Candidates, the protected ones
    and the non-protected ones

    TODO: write proper documentation

    Member:
    ------
    __prottAttr : string
        defines what sex shall be the protected attribute, i.e. determines whether males or females
        are the protected group

    """

    @property
    def protectedCandidates(self):
        return self.__protectedCandidates


    @property
    def nonProtectedCandidates(self):
        return self.__nonProtectedCandidates


    @property
    def originalOrdering(self):
        return self.__originalOrdering


    def __init__(self, path, protectedAttributeDef):
        self.__protectedCandidates = []
        self.__nonProtectedCandidates = []
        self.__originalOrdering = []
        self.__path = path
        self.__protAttr = protectedAttributeDef


    def __determineIfProtected(self, r):
        """
        takes a JSON profile and finds if the person belongs to the protected group

        Parameter:
        ---------
        r : JSON node
        a person description in JSON, everything below node "profile"

        TODO: should maybe not always use the same protattr, je nachdem ob die query male oder female dominated war...vllt mehr finetunig?
        """

        if 'sex' in r['profile'][0]:
            if r['profile'][0]['sex'] == self.__protAttr:
                # print(">>> protected\n")
                return True
            else:
                # print('>>> non-protected\n')
                return False
        else:
            print('>>> undetermined\n')
            return False


    def __determineWorkMonths(self, job_with_no_dates, job_with_same_year, job_with_undefined_dates, r):
        """
        takes a person's profile as JSON node and computes the total amount of work months this
        person has

        Parameters:
        ----------
        r : JSON node


        """
        total_working_months = 0  # ..of that profile
        job_duration = 0

        if len(r['profile'][0]) > 4:  # a job is on the profile
            list_of_Jobs = r['profile'][0]['jobs']
            # print('profile summary' + str(r['profile'][0]['jobs']))
            for count in range(0, len(list_of_Jobs)):
                if len(list_of_Jobs[count]) > 3:  # an exact duration is given at 5 nodes!

                    job_duration_string = list_of_Jobs[count]['jobDates']
                    if job_duration_string == 'bis heute':
                        # print('job with no dates found - will be count for ' + str(job_with_no_dates) + ' months.')
                        job_duration = job_with_no_dates

                    else:
                        job_start_string, job_end_string = job_duration_string.split(' - ')

                        if len(job_start_string) == 4:
                            job_start = datetime.datetime.strptime(job_start_string, "%Y")
                        elif len(job_start_string) == 7:
                            job_start = datetime.datetime.strptime(job_start_string, "%m/%Y")
                        else:
                            print("error reading start date")

                        if len(job_end_string) == 4:
                            job_end = datetime.datetime.strptime(job_end_string, "%Y")
                        elif len(job_end_string) == 7:
                            job_end = datetime.datetime.strptime(job_end_string, "%m/%Y")
                        else:
                            print("error reading end date")

                        if job_end - job_start == 0:
                            delta = job_with_same_year
                        else:
                            delta = job_end - job_start

                        job_duration = math.ceil(delta.total_seconds() / 2629743.83)

                        # print(job_duration_string)
                        # print('this job: ' + str(job_duration))

                total_working_months += job_duration
                # print('total jobs: ' + str(total_working_months))

            # print("working: " +  str(total_working_months))
        else:
            # print('-no jobs on profile-')
            pass

        return total_working_months

    def __determineEduMonths(self, edu_with_no_dates, edu_with_same_year, edu_with_undefined_dates, r):
        """
        takes a person's profile as JSON node and computes the total amount of work months this
        person has

        Parameters:
        ----------
        r : JSON node


        """
        total_education_months = 0  # ..of that profile
        edu_duration = 0

        if 'education' in r:  # education info is on the profile
            list_of_edu = r['education']  # edu child nodes {institution, url, degree, eduDuration}
            # print('education summary' + str(r['education']))
            for count in range(0, len(list_of_edu)):
                if 'eduDuration' in list_of_edu[count]:  # there are education dates

                    edu_duration_string = list_of_edu[count]['eduDuration']
                    if edu_duration_string == ('bis heute' or None or ''):
                        edu_duration = edu_with_no_dates
                    else:
                        edu_start_string, edu_end_string = edu_duration_string.split(' - ')

                        if len(edu_start_string) == 4:
                            edu_start = datetime.datetime.strptime(edu_start_string, "%Y")
                        elif len(edu_start_string) == 7:
                            edu_start = datetime.datetime.strptime(edu_start_string, "%m/%Y")
                        else:
                            print("error reading start date")

                        if len(edu_end_string) == 4:
                            edu_end = datetime.datetime.strptime(edu_end_string, "%Y")
                        elif len(edu_end_string) == 7:
                            edu_end = datetime.datetime.strptime(edu_end_string, "%m/%Y")
                        else:
                            print("error reading end date")

                        if edu_end - edu_start == 0:
                            delta = edu_with_same_year
                        else:
                            delta = edu_end - edu_start

                        edu_duration = math.ceil(delta.total_seconds() / 2629743.83)

                        # print(job_duration_string)
                        # print('this job: ' + str(job_duration))

                else: edu_duration = edu_with_no_dates

                total_education_months += edu_duration
                # print('total jobs: ' + str(total_working_months))

            # print("studying: " + str(total_education_months))
        else:
            # print('-no education on profile-')
            pass

        return total_education_months

    def simulateRankDump(self, pairsOfPAndAlpha):
        """
        loops over all .json files and collects the profile information from Xing into two data
        structures. All protected candidates and their scores (length of job experience) are put
        into an array of Candidate objects, all non-protected Candidate objects are put into a
        different array

        """

        """
        FIXME: quick and dirty fix to have separate data structures for each search query
        should be done without a local array, maybe don't use a class anymore
        """

        files = glob.glob(self.__path)
        eduOrJob_with_no_dates = 3  # months count if you had a job that has no associated dates
        eduOrJob_with_same_year = 6  # months count if you had a job that started and finished in the same year
        eduOrJob_with_undefined_dates = 1  # month given that the person entered the job
        print("loaded ", files)  # list of files to analyze

        for filename in files:
            # FIXME: see FIXME above, we are using a new data structure to separate each category
            # data from each other...very dirty

            protected_count = 0
            nonprotected_count = 0
            score_array = []
            sex_array = []

            self.__nonProtectedCandidates = []
            self.__protectedCandidates = []
            self.__originalOrdering = []

            currentfile = open(filename)  # filestream
            data = json.load(currentfile)
            xingSearchQuery = data['category']
            k = len(data['profiles'])
            print('\n\n %% category ' + xingSearchQuery + ' has ' + str(k) + ' entries\n')

            identifier = 0  # TODO: yangStoyanovich ID explain why using it

            for r in data['profiles']:
                # determine Member since / Hits
                if 'memberSince_Hits' in r['profile'][0]:
                    hits_string = r['profile'][0]['memberSince_Hits']
                    member_since, hits = hits_string.split(' / ')
                    # print(str(hits))
                work_experience = self.__determineWorkMonths(eduOrJob_with_no_dates, eduOrJob_with_same_year,
                                                            eduOrJob_with_undefined_dates, r)
                edu_experience = self.__determineEduMonths(eduOrJob_with_no_dates, eduOrJob_with_same_year,
                                                          eduOrJob_with_undefined_dates, r)
                score = (work_experience + edu_experience) * int(hits)

                # print('profile score: 1000 * ' + str(score) + '\n(' + str(work_experience) + ' + '
                #       + str(edu_experience) + ') / ' + str(hits))
                score_array.append(str(round(score, 2)))

                if self.__determineIfProtected(r):
                    self.__protectedCandidates.append(Candidate(score, ProtectedAttribute(self.__protAttr), identifier))
                    self.__originalOrdering.append(Candidate(score, ProtectedAttribute(self.__protAttr), identifier))
                    identifier += 1
                    protected_count += 1
                    sex_array.append("Prtcd")  # protected
                else:
                    self.__nonProtectedCandidates.append(Candidate(score, [], identifier))
                    self.__originalOrdering.append(Candidate(score, [], identifier))
                    identifier += 1
                    nonprotected_count += 1
                    sex_array.append("nPrtcd")  # nonprotected

            self.__protectedCandidates.sort(key=lambda candidate: candidate.qualification, reverse=True)
            self.__nonProtectedCandidates.sort(key=lambda candidate: candidate.qualification, reverse=True)

            # hier sind alle Kandidaten einer Kategorie eingesammelt...man könnte die hier schon ranken und das Ranking dumpen
            # FIXME: alles umziehen und zusammen bündeln, sodass das rausschreiben auf die Platte nur an einer Stelle gemacht wird

            normalizeQualifications(self.__protectedCandidates + self.__nonProtectedCandidates)
            normalizeQualifications(self.__originalOrdering)

            dumpRankingsToDisk(self.__protectedCandidates, self.__nonProtectedCandidates, k, xingSearchQuery,
                               "../files/results/rankingDumps/Xing/" + xingSearchQuery, pairsOfPAndAlpha)
            if not os.path.exists(os.getcwd() + "/../files/results/rankingDumps/Xing/" + xingSearchQuery + '/'):
                os.makedirs(os.getcwd() + "/../files/results/rankingDumps/Xing/" + xingSearchQuery + '/')
            writePickleToDisk(self.__originalOrdering,
                              os.getcwd() + "/../files/results/rankingDumps/Xing/" + xingSearchQuery + '/' + xingSearchQuery + 'OriginalOrdering.pickle')

            # ratio protected/unprotected
            print(str(sex_array) + "\n" + str(score_array))
            print("Ratio: " + str(protected_count) + " : " + str(nonprotected_count))
            print("in %: " + str(protected_count / (protected_count + nonprotected_count)) + " : " +
                  str(nonprotected_count / (protected_count + nonprotected_count)))
            currentfile.close()

