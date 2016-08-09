# -*- coding: utf-8 -*-
from __future__ import division

import logging
import requests
import time

from .parsing.amendement_parser import parse_amendements_summary
from .parsing.question_search_result_parser import parse_question_search_result

__all__ = ['AmendementSearchService', 'QuestionSearchService']

LOGGER = logging.getLogger(__name__)


class AmendementSearchService(object):
    def __init__(self):
        self.base_url = "http://www2.assemblee-nationale.fr/recherche/query_amendements"  # noqa
        self.default_params = {
            'texteRecherche': None,
            'numAmend': None,
            'idArticle': None,
            'idAuteur': None,
            'idDossierLegislatif': None,
            'idExamen': None,
            'idExamens': None,
            'periodeParlementaire': None,
            'dateDebut': None,
            'dateFin': None,
            'rows': 100,
            'start': None,
            'sort': None,
            'format': 'html',
            'tri': 'ordreTexteasc',
            'typeRes': 'liste',
            'typeDocument': 'amendement',
        }

    def get(self, **kwargs):
        """
        :param texteRecherche:
        :param numAmend:
        :param idArticle:
        :param idAuteur:
        :param idDossierLegislatif:
        :param idExamen:
        :param idExamens:
        :param periodeParlementaire:
        :param dateDebut:
        :param dateFin:
        :param rows:
        :param start:
        :param sort:
        """
        params = self.default_params.copy()
        params.update(kwargs)

        start = time.time()
        response = requests.get(self.base_url, params=params)
        end = time.time()

        LOGGER.debug(
            'fetched amendements with search params: %s in %0.2f s',
            params,
            end - start
        )

        return parse_amendements_summary(response.url, response.json())

    def total_count(self, **kwargs):
        kwargs_copy = kwargs.copy()
        kwargs_copy['rows'] = 1
        response = self.get(**kwargs_copy)
        return response.total_count

    def iterator(self, **kwargs):
        rows = kwargs.get('rows', self.default_params['rows'])

        response = self.get(**kwargs)

        LOGGER.debug('start to fetch %s amendements with page size of %s',
                     response.total_count,
                     rows)
        LOGGER.debug('amendements fetched: %s / %s (%.1f%%)',
                     rows,
                     response.total_count,
                     rows / response.total_count * 100)

        yield response

        for start in range(rows, response.total_count, rows):
            LOGGER.debug('amendements fetched: %s / %s (%.1f%%)',
                         rows + start,
                         response.total_count,
                         (rows + start) / response.total_count * 100)
            kwargs_copy = kwargs.copy()
            kwargs_copy['start'] = start + 1
            yield self.get(**kwargs_copy)

    def get_order(self, **kwargs):
        iterator = AmendementSearchService().iterator(**kwargs)
        order = []
        for it in iterator:
            order += [amendement.num_amend for amendement in it.results]
        return order


class QuestionSearchService(object):
    def __init__(self):
        self.base_url = 'http://www2.assemblee-nationale.fr/'
        self.search_url = '%srecherche/resultats_questions' % self.base_url
        self.default_params = {
            'limit': 10,
            'legislature': None,
            'replies[]': None,  # ar, sr
            'removed[]': None,  # 0,1
            'ssTypeDocument[]': 'qe',
        }

    def get(self, legislature=14, is_answered=None, is_removed=None, size=10):
        params = self.default_params.copy()

        if is_answered:
            is_answered = 'ar'
        elif is_answered is not None:
            is_answered = 'sr'
        if is_removed is not None:
            is_removed = int(is_removed)

        params.update({
            'legislature': legislature,
            'limit': size,
            'replies[]': is_answered,
            'removed[]': is_removed
        })
        response = requests.post(self.search_url, data=params)

        return parse_question_search_result(response.url, response.content)

    def total_count(self, legislature=14, is_answered=None, is_removed=None):
        return self.get(legislature=legislature, is_answered=is_answered,
                        is_removed=is_removed, size=1).total_count

    def iter(self, legislature=14, is_answered=None, is_removed=None, size=10):
        search_results = self.get(legislature=legislature,
                                  is_answered=is_answered,
                                  is_removed=is_removed, size=size)
        yield search_results

        for start in range(1, search_results.total_count, size):
            if search_results.next_url is not None:
                yield parse_question_search_result(
                    search_results.next_url,
                    requests.get(self.base_url +
                                 search_results.next_url).content)
