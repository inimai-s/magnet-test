# OTTO_TESTS.PY
# all relevant functions to query magnet tests from otto results database

import requests
import pandas as pd

DEFAULT_HOST_LOCATION = 'https://otto-results.spacex.corp'
DEFAULT_API_PATH = '/api/v1/'


# query a request from the database
def query(host, path, query_string):
    """query the database"""
    url = "{}{}{}".format(host, path, query_string)
    return requests.get(url).json()


# return a result for a query
def grab_document(host, path, case_id):
    """
    Return a Result object
    Args:
        host: host of database
        path: api path
        case_id(string): identifier for the testcase you are parsing. EG: '98df0ff4-6256-4a2a-b193-fce64cb6ccf1'
    """
    return Result(case_id=case_id, db_dict=query(host, path, "documents/{}".format(case_id)))


# result class that stores information for a test
class Result(object):
    """Structure of a testcase result as stored in the database"""

    def __init__(self, case_id, db_dict, host_location=DEFAULT_HOST_LOCATION):
        """input a dictionary that is a result of querying the database for a document"""
        self.case_id = case_id
        self.otto = '{}/report/{}'.format(host_location, case_id)
        self.date = db_dict['completed']
        self.description = db_dict['description']
        self.links = db_dict['links']
        self.measurements = db_dict['measurements']
        self.name = db_dict['name']
        self.outcome = db_dict['outcome']
        self.production_test = db_dict['production_test']
        self.references = db_dict['references']
        self.requirements = db_dict['requirements']
        self.rules = db_dict['rules']
        self.started = db_dict['started']
        self.steps = db_dict['steps']
        self.tags = db_dict['tags']
        self.test_system = db_dict['test_system']
        self.tools = db_dict['tools']
        self.document_uuid = db_dict['uuid']
        self.version = db_dict['version']

    def __str__(self):
        return "\nCASE ID: %s\nProduction Test: %s\nLINK: %s\nOUTCOME: %s\n" % (self.case_id, self.name, self.otto_link, self.outcome)

    @staticmethod
    def _loop_first(structure, key_id, key_value, value_id, empty_response=''):
        """property helper to grab first key value"""
        for item in structure:
            if item[key_id] == key_value:
                return item[value_id]
        return empty_response

    @property
    def issue_ticket(self):
        """Return a borg link"""
        return self._loop_first(self.links, 'name', 'issue_ticket', 'path')
    
    @property
    def otto_link(self):
        """Return a borg link"""
        return self._loop_first(self.links, 'name', 'otto_results', 'path')
    
    @property
    def borg(self):
        """Return a otto db link"""
        return 'https://borg.spacex.corp/runs/{}'.format(
            self._loop_first(self.links, 'name', 'borg_run_id', 'path'))

    @property
    def pcba_uuid(self):
        """Return the units pcba uuid"""
        return self._loop_first(self.references, 'ref_type', 'pcba_uuid', 'ref_id')

    @property
    def campaign_id(self):
        """Return the campaign id"""
        return self._loop_first(self.references, 'ref_type', 'campaign_id', 'ref_id')

    @property
    def user(self):
        """Return running user"""
        return self._loop_first(self.references, 'ref_type', 'borg_user', 'ref_id')

    @property
    def slot(self):
        """Return running slot"""
        return self._loop_first(self.references, 'ref_type', 'slot_number', 'ref_id')

    @property
    def sn(self):
        """Return serial number"""
        return self._loop_first(self.references, 'ref_type', 'serial_number', 'ref_id')
    
    @property
    def pn(self):
        """Return serial number"""
        return self._loop_first(self.references, 'ref_type', 'part_number', 'ref_id')
    
    @property
    def workorder(self):
        """Return serial number"""
        return self._loop_first(self.references, 'ref_type', 'warp_workorder', 'ref_id')


# otto query class that is used to query the database
class OttoQuery(object):
    """helper to query otto-results"""

    def __init__(self, host_location=None, api_path=None):
        self.host = host_location or DEFAULT_HOST_LOCATION
        self.path = api_path or DEFAULT_API_PATH

    def _query(self, query_string):
        return query(self.host, self.path, query_string)

    def get_results_by_reference(self, query_string, sort_by=None):
        """query the database"""
        results = []

        total_items = self._query(f'{query_string}&items_per_page=1')['total_items']
        result_pointers = self._query(f'{query_string}&items_per_page={total_items}')

        for result_pointer in result_pointers['items']:
            try:
                results.append(grab_document(self.host, self.path, case_id=result_pointer['case_id']))
            except KeyError:
                pass

        if sort_by:
            results = sorted(results, key=lambda i: i.__getattribute__(sort_by), reverse=True)
        return results

    def sn_results(self, *serial_numbers):
        """Get all results with the serial number"""
        return self._results(*serial_numbers, ref_type='serial_number')

    def pcba_uuid_results(self, *pcba_uuid):
        """Get all results with the pcba_uuid"""
        return self._results(*pcba_uuid, ref_type='pcba_uuid')

    def any_results(self, *search_value):
        """Get all results with a reference value equal to the the input"""
        return self._results(*search_value)

    def _results(self, *values: str, **kwargs):
        """

        kwargs:
          ref_type: str  the reference type
          sort_by:  str  the sort by or 'date' default
        """
        if 'ref_type' in kwargs:
            query_url = 'references?reference_type={}'.format(kwargs['ref_type'])
        else:
            # Flask won't care that an ampersand follows a question mark
            query_url = 'references?'

        for val in values:
            query_url = query_url + '&reference_value={}'.format(val)

        return self.get_results_by_reference(query_url, sort_by=kwargs.get('sort_by', 'date'))



# query to otto results database
otto = OttoQuery(DEFAULT_HOST_LOCATION, DEFAULT_API_PATH)


# find all magnet tests that correspond to a list of test serial numbers that correspond to specific part numbers
def find_magnet_test_groups(snpndict):
    radial_tests = []
    axial_inner_tests = []
    axial_outer_tests = []

    for test_id in snpndict.keys():
        for result in otto.sn_results(test_id):
            if 'magnet' in result.name and result.outcome == 'pass' and any(elem in result.pn for elem in snpndict[test_id]):

                if 'Radial' in result.name:
                    radial_tests.append(result)

                elif 'Axial' in result.name:
                    for i in result.steps:
                        if 'against expected properties' in i['description']:
                            for entry in i['measurements']:
                                if entry[1]['name'] == 'Average Magnetic Flux': # determine whether axial test is for the inner or outer magnets since inner magnets have higher flux
                                    if entry[1]['value'] < 700:
                                        axial_outer_tests.append(result)
                                    else:
                                        axial_inner_tests.append(result)
                                    break

    return radial_tests,axial_inner_tests,axial_outer_tests


# find the latest test for each type of scan
def find_latest_magnet_tests(test_id_list):
    radial_tests,axial_inner_tests,axial_outer_tests = find_magnet_test_groups(test_id_list)
    final_tests = []

    if len(radial_tests) > 0:
        latest_radial = pd.to_datetime(radial_tests[0].date)
        final_radial_test = radial_tests[0]
        for test in radial_tests:
            new_date = pd.to_datetime(test.date)
            if new_date > latest_radial:
                latest_radial = new_date
                final_radial_test = test
        final_tests.append(final_radial_test)

    if len(axial_inner_tests) > 0:
        latest_inner_axial = pd.to_datetime(axial_inner_tests[0].date)
        final_axial_inner_test = axial_inner_tests[0]
        for test in axial_inner_tests:
            new_date = pd.to_datetime(test.date)
            if new_date > latest_inner_axial:
                latest_inner_axial = new_date
                final_axial_inner_test = test
        final_tests.append(final_axial_inner_test)

    if len(axial_outer_tests) > 0:
        latest_outer_axial = pd.to_datetime(axial_outer_tests[0].date)
        final_axial_outer_test = axial_outer_tests[0]
        for test in axial_outer_tests:
            new_date = pd.to_datetime(test.date)
            if new_date > latest_outer_axial:
                latest_outer_axial = new_date
                final_axial_outer_test = test
        final_tests.append(final_axial_outer_test)

    return final_tests


# reformat a test into a dictionary that stores all the data information
def generate_magnet_test_entry(result,sat):
    measurement_dict = {}

    measurement_dict['sxid'] = sat
    measurement_dict['test_sn'] = result.sn
    measurement_dict['pn'] = result.pn
    measurement_dict['test_type'] = 'magnet'
    measurement_dict['date'] = result.date
    measurement_dict['test_id'] = result.case_id
    measurement_dict['otto_link'] = result.otto
    measurement_dict['name'] = result.name
    measurement_dict['outcome'] = result.outcome

    for i in result.steps:
        if 'Collect Magnetic' in i['description']:
            for entry in i['measurements']:
                measurement_dict['unit'] = entry[1]['unit']
                measurement_dict[entry[1]['name'][(entry[1]['name'].find('flux')):]] = entry[1]['value']
        elif 'against expected properties' in i['description']:
            for entry in i['measurements']:
                measurement_dict[entry[1]['name']] = entry[1]['value']
                
    if 'Radial' in result.name:
        measurement_dict['magnet_view'] = 'radial'
        measurement_dict['magnet_type'] = 'combined'
    elif 'Axial' in result.name:
        measurement_dict['magnet_view'] = 'axial'
        if measurement_dict['Average Magnetic Flux'] < 700:
            measurement_dict['magnet_type'] = 'outer'
        else:
            measurement_dict['magnet_type'] = 'inner'              

    return measurement_dict
