# -*- coding: utf-8 -*-
#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2018  Carl Hage
# Copyright (C) 2018  Chris Jerdonek
#
# This file is part of Open Source Voting Results Reporter (ORR).
#
# ORR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""
Class definitions to represent an election definition, with
contests containing a list of choices, either an OfficeContest with list
of candidates or MeasureContest with list of named choices, usually
yes/no.
"""

from collections import OrderedDict

# Besides the votes for candidates and measure choices counted, there
# are a set of summary results with ballots not counted by category,
# and a summary result for totals. These have a set of IDs and a generic title.
# For n of m voting (Vote for n), a voter can make n selections, so for
# "vote for 3", if only 1 choice was made, there would be 2 undervotes,
# and if 4 or more choices were made, there would be 3 overvotes
RESULT_ATTRIBUTES = OrderedDict([
    ('SVTot', 'Ballots Counted'),   # Sum of valid votes reported
    ('SVCst', 'Ballots Cast'),      # Ballot sheets submitted by voters
    ('SVReg', 'Registered Voters'), # Voters registered for computing turnout
    ('SVTrn', 'Voter Turnout'),     # (SVCst/SVReg)*100
    ('SVRej', 'Ballots Rejected'),  # Not countable
    ('SVUnc', 'Ballots Uncounted'), # Not yet counted or needing adjudication
    ('SVWri', 'Writein Votes'),     # Write-in candidates not explicitly listed
    ('SVUnd', 'Undervotes'),        # Blank votes or additional votes not made
    ('SVOvr', 'Overvotes'),         # Possible votes rejected by overvoting
    ('SVExh', 'Exhausted Ballots')  # All RCV choices were eliminated (RCV only)
    ])

# Both detailed reports and contest summary reports might list a vote
# total as well as one or more subtotals. A set of ID/Suffix codes and
# a name/title is predefined. An RCV contest will also have RCV Round subtotals
SUBTOTAL_TYPES = OrderedDict([
    ('TO','Total'),             # Total of all subtotals
    ('ED','Election Day'),      # Election day precinct voting (in county)
    ('MV','Vote by Mail'),     # Vote by mail ballots (in county)
    ('EV','Early Voting'),      # Early voting/vote centers (in county)
    ('XA','Outside County'),    # Votes from other counties (multi-county contest)
    ('OA','In-County Total')    # Subtotal this county only (multi-county contest)
    ])

def append_id_index(idlist,index:dict,obj,
                    errmsg="duplicate id"):
    """
    This routine contains common code for appending an object to an
    ordered list, with an index dictionary to reference the object
    by id.

    Args:
        idlist: a list this object will be appended
        index:  a dict to lookup by obj.id
        obj:    object to be added
        errmsg: object specific error message (optional)
    """
    if not obj.id:
        raise RuntimeError('A unique ID is required')
    if obj.id in index:
        raise RuntimeError(errmsg)
    obj.index = len(idlist)   # Assign a sequence
    idlist.append(obj)
    index[obj.id] = obj


def append_result_subtotal(contest,obj,data:dict,listattr:list):
    """
    This routine contains common processing to append a
    SubtotalType or ResultDetail to a list within the contest.

    Args:
        contest:    contest containing the listattr
        obj:        object to be appended
        data:       source data to copy
        listattr:   list attribute or contest to append
    """
    obj.from_data(data)         # Copy data
    obj.index = len(listattr)   # Assign a sequence
    obj.contest = contest       # Back reference
    listattr.append(obj)

def copy_from_data(obj:dict, data:dict, handler:dict={}):
    """
    Copies data from a loaded dict into an object. If a key is found
    with a handler, then the handler function is called.

    Args:
        obj: an object with data loaded
        data: a dict with attributes and values to copy
        handler: a dict of attribute names with a special handler function
                 (handlers process arrays with member objects to create/copy)
    """
    for k, v in data:
        if k in handler:
            # This attribute will be processed with a handler function
            handler[k](obj,v)
        else:
            # All others are just copied
            obj[k] = v

def enter_ballot_items(election,data:dict):
    """
    Creates a new Header, OfficeContest, MeasureContest, or YNOfficeContest
    object from a dict. The 'type' attribute will identify which item
    """

class Election:
    """
    The election is the root object for all content defined for an
    election operated by an Election Administration (EA), e.g. a
    county.

    An Election object without a date can be used to hold a definition
    of all current elected offices, represented as a contest and incumbents
    represented as candidate objects.
    """

    def __init__(self):
        # Initialize the lists and dictionaries
        self.ballot_items = []  # ordered list of headers and contests
        self.ballot_items_by_id = {} # index of headers and contests by id

    def from_data(self,data:dict):
        """
        The from_data will copy string attributes from an external attribute:value
        dict, expanding the member ballot_items.
        """
        copy_from_data(self,data,{'ballot_items':Election.enter_ballot_items })


    def enter_ballot_items(self,ballot_items:list):
        """
        Scan the list of source data representing ballot items.
        """
        for bi_input in ballot_items:
            if bi_input.type == 'header':
                bi = Header()
            elif bi_input.type == 'office':
                bi = OfficeContest()
            elif bi_input.type == 'measure':
                bi = MeasureContest()
            elif bi_input.type == 'ynoffice':
                bi = YNOfficeContest()
            else:
                raise RuntimeError('Invalid ballot item type')
            bi.from_data(bi_input)
            if bi.get('header_id',None):
                # Add this bi to the header's bi list
                header = self.ballot_items_by_id.get(bi.header_id, None)
                if not header:
                    raise RuntimeError(f'Unknown header id "{bi.header_id}"')
                header.ballot_items.append(bi)
                bi.header = header  # back reference
            else bi.header = None
            append_id_index(self.ballot_items,self.ballot_items_by_id,bi)


class BallotItem:
    """
    The BallotItem are items that appear on ballots-- either headers or
    contests. Each ballot item can be a subitem of a parent header.
    All BallotItems have the following common attributes:
      header_id: id of parent header object containing this item or 0 for root
      id: must be unique across all contests or headers
      ballot_title: text appearing on ballots representing the header/contest
      ballot_subtitle: second level title for this item
      """
    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        self.id = id_
        self.ballot_subtitle = ballot_subtitle
        self.ballot_title = ballot_title

class Header(BallotItem):
    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        BallotItem.__init__(self,id_,ballot_title,ballot_subtitle)
        self.ballot_items = []

    def from_data(self,data:dict):
        copy_from_data(self,data)


class Contest(BallotItem):
    """
    The contest is a superclass of all contest types: offices, measures,
    and retention/recall. All contests have the following common attributes:
      id: must be unique across all contests or headers
      short_title: Short name for a contest usable in reports independent of
                   headers
      ballot_title: text appearing on ballots representing the contest
      choices: List of choices: candidates or Yes/No etc. on measures
               and recall/retention contests
    """

    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        BallotItem.__init__(self,id_,ballot_title,ballot_subtitle)
        self.choices = []           # ordered list of all contest choices
        self.result_attributes = [] # Pseudo choice for result summary attrs
        self.choices_by_id = {}     # index of choices by id
        self.subtotal_types = []    # summary subtotals available
        self.result_details = []    # result detail definitions

    def enter_result_attributes(self,result_attributes):
        """
        Scan summary result attributes for a contest
        """
        for c_input in result_attributes:
            c = ResultAttribute()
            c.from_data(c_input)
            append_id_index(self.result_attributes,self.choices_by_id,c)

    def enter_subtotal_types(self,subtotal_types):
        """
        Scan summary subtotals available for this contest
        """
        for s_input in subtotal_types:
            append_result_subtotal(self,SubtotalType(),
                                       s_input,self.subtotal_types)

    def enter_result_details(self,result_details):
        """
        Scan detail subtotals available for this contest
        """
        for s_input in result_details:
            append_result_subtotal(self,ResultDetail(),
                                       s_input,self.result_details)

    def enter_choice(self,choice,choice_input):
        """
        Common processing to enter a candidate or measure choice
        """
        enter_choicec.from_data(choice_input)
        choice.contest = self     # Add back reference
        append_id_index(self.choices,self.choices_by_id,choice)


class OfficeContest(Contest):
    """
    The OfficeContest represents an elected office where choices are
    a set of candidates.
    """
    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        Contest.__init__(self,id_,ballot_title,ballot_subtitle)

    def from_data(self,data:dict):
        copy_from_data(self,data,{
            'choices':OfficeContest.enter_candidates,
            'result_attributes':Contest.enter_result_attributes})

    def enter_candidates(self,candidates):
        """
        Scan an input data list of candidate entries to create
        """
        for c_input in candidates:
            c = Contest.enter_choice(self,Candidate(),c_input)


class MeasureContest(Contest):
    """
    The MeasureContest represents a ballot measure question posed to voters.
    Most measures have a Yes/No question though the text that can appear on
    ballots for the response may be different, e.g. "Bonds Yes". For a
    yes/no question, the measure will pass or fail, depending on the approval
    required. Normally, the first choice is yes. Some measures might be
    multiple choice, e.g. preferred name of a proposed city, and might
    have more than 2 choices. Ranked Choice Voting could be used with a
    multiple choice measure.
    """

    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        Contest.__init__(self,id_,ballot_title,ballot_subtitle)

    def from_data(self,data:dict):
        copy_from_data(self,data,{
            'choices':MeasureContest.enter_choices,
            'result_attributes':Contest.enter_result_attributes})

    def enter_choices(self,choices):
        """
        Scan an input data list of measure choie entries to create
        """
        for c_input in choices:
            c = Contest.enter_choice(self,Choice(),c_input)

class YNOfficeContest(MeasureContest):
    """
    A YNOfficeContest is a hybrid of MeasureContest and OfficeContest,
    used for approval voting (retention contest) or for a recall question.
    The attributes defining an elected office are included, and information
    on the incumbent/candidate can be defined.
    """
    def __init__(self,id_=None,ballot_title=None,ballot_subtitle=""):
        Contest.__init__(self,id_,ballot_title,ballot_subtitle)

    def from_data(self,data:dict):
        # In orr we don't need to distinguish with a measure
        MeasureContest.from_data(self,data)

class Choice:
    """
    Choice represents a selection on a ballot-- a candidate for an elected
    office, or Yes/No for a ballot measure, retention or recall office.
    Multiple choice for a measure is a selection other than yes/no for
    a pass/fail contest, e.g. preferred name of a proposed city incorporation.
    """
    def __init__(self,id_=None,ballot_title=None):
        self.id = id_
        self.ballot_title = ballot_title

    def from_data(self,data:dict):
        copy_from_data(self,data)


class Candidate(Choice):
    """
    A candidate can have additional attributes
    """
    def __init__(self,id_=None,ballot_title=None):
        Choice.__init__(self,id_,ballot_title)

    def from_data(self,data:dict):
        copy_from_data(self,data)

class ResultAttribute(Choice):
    """
    Besides votes for a candidate or measure choice, a set of vote/ballot
    totals are computed for a set of summary attributes that represent
    rejected votes and totals. The RESULT_ATTRIBUTES contain an id
    (that is distinct from a candidate/choice id) and "ballot_title"
    that can be used as a label in a report analogous to a candidate/choice name.
    """
    def __init__(self,id_=None,ballot_title=None):
        Choice.__init__(self,id_,ballot_title)

    def from_data(self,data:dict):
        copy_from_data(self,data)

class SubtotalType:
    """
    When reporting summary data, the votes reported may include a total
    as well as a set of contest or election configurable subtotals. For
    detailed data with precinct and district breakdowns, each area subtotal
    may have separated subtotal types, e.g. election day precinct voting,
    and vote-by-mail. An object is defined to hold a reference id as well
    as a label.
    """

    def __init__(self,id_=None,heading=None):
       self.id = id
       self.heading = heading

    def from_data(self,data:dict):
        copy_from_data(self,data)

class ResultDetail:
    """
    When reporting detailed results data, a set of separate total/subtotal
    exists for a set of ResultDetail
    """

    def __init__(self,id_=None,area_heading=None,subtotal_heading=None,
                 is_vbm=False):
       self.id = id
       self.area_heading = area_heading
       self.subtotal_heading =subtotal_heading
       self.is_vbm = is_vbm

    def from_data(self,data:dict):
        copy_from_data(self,data)