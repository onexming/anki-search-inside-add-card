import re
import time
import json
import os
import math
from datetime import datetime
from aqt import mw
from aqt.utils import showInfo, tooltip
# lazy solution for running output from test dir
try:
    from .debug_logging import log
    from .stats import getRetentions
    from .state import get_index
    from .notes import get_pdf_info
except:
    from debug_logging import log
    from stats import getRetentions
    from state import get_index
    from notes import get_pdf_info

import utility.tags
import utility.text
import utility.misc

class Output:

    def __init__(self):
        #todo: cleanup
        self.editor = None
        self.SEP_RE = re.compile(r'(?:\u001f){2,}|(?:\u001f[\s\r\n]+\u001f)')
        self.SEP_END = re.compile(r'</div>\u001f$')
        self.SOUND_TAG = re.compile(r'sound[a-zA-Z0-9]*mp')
        self.IO_REPLACE = re.compile('<img src="[^"]+(-\d+-Q|-\d+-A|-(<mark>)?oa(</mark>)?-[OA]|-(<mark>)?ao(</mark>)?-[OA])\.svg" ?/?>(</img>)?')
        self.IMG_FLD =  re.compile('\\|</span> ?(<img[^>]+/?>)( ?<span class=\'fldSep\'>|$)')
        self.latest = -1
        self.wordToken = re.compile(u"[a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.I | re.U)
        self.gridView = False
        self.stopwords = []
        self.plotjsLoaded = False
        self.showRetentionScores = True
        self.lastResults = None
        self.hideSidebar = False
        self.uiVisible = True
        # saved to display the same time taken when clicking on a page other than 1
        self.last_took = None
        self.last_had_timing_info = False

        #determines the zoom factor of rendered notes
        self.scale = 1.0

        #cache previous calls
        self.previous_calls = []


        self.noteTemplate = """<div class='cardWrapper %s' id='nWr-%s'>
                            <div class='topLeftWr'>
                                <div id='cW-%s' class='rankingLbl' onclick="expandRankingLbl(this)">%s<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div>
                                %s
                            </div>
                            <div id='btnBar-%s' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='editLbl' onclick='edit(%s)'>Edit</div>
                                <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                                <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div>
                                <div class='floatLbl' onclick='addFloatingNote(%s)'>&#10063;</div>
                                <div id='rem-%s' class='remLbl' onclick='removeNote(%s)'><span>&times;</span></div>
                            </div>
                            <div class='cardR' onmouseup='getSelectionText()' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div>
                            <div id='tags-%s'  style='position: absolute; bottom: 0px; right: 0px;'>%s</div>
                            <div class='cardLeftBot' onclick='expandCard(%s, this)'>&nbsp;INFO&nbsp;</div>
                        </div>"""

        self.noteTemplateSimple = """<div class='cardWrapper' style="display: block;">
                            <div class='topLeftWr'>
                                <div class='rankingLbl'>%s<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div>
                                %s
                            </div>
                            <div class='btnBar' id='btnBarSmp-%s' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='editLbl' onclick='edit(%s)'>Edit</div>
                            </div>
                            <div class='cardR' onmouseup='%s'  onmouseenter='cardMouseEnter(this, %s, "simple")' onmouseleave='cardMouseLeave(this, %s, "simple")'>%s</div>
                            <div style='position: absolute; bottom: 0px; right: 0px;'>%s</div>
                            <div class='cardLeftBot' onclick='expandCard(%s, this)'>&nbsp;INFO&nbsp;</div>
                        </div>"""

        self.noteTemplateUserNoteSimple = """<div class='cardWrapper' style="display: block;">
                            <div class='topLeftWr'>
                                <div class='rankingLbl'>%s<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div>
                                %s
                            </div>
                            <div class='btnBar' id='btnBarSmp-%s' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='editLbl' onclick='pycmd("siac-edit-user-note %s")'>Edit</div>
                            </div>
                            <div class='cardR' onmouseup='%s'  onmouseenter='cardMouseEnter(this, %s, "simple")' onmouseleave='cardMouseLeave(this, %s, "simple")'>%s</div>
                            <div style='position: absolute; bottom: 0px; right: 0px;'>%s</div>
                            <div class='cardLeftBot' style='display: none' onclick='%s'></div>
                        </div>"""

        self.noteTemplateUserNote = """<div class='cardWrapper %s' id='nWr-%s'>
                            <div class='topLeftWr'>
                                <div id='cW-%s' class='rankingLbl'>%s &nbsp;SIAC<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div>
                                %s
                            </div>
                            <div id='btnBar-%s' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='deleteLbl' onclick='pycmd("siac-delete-user-note-modal %s"); '><div class='siac-trash-icn'></div></div>
                                <div class='editLbl' onclick='pycmd("siac-edit-user-note %s")'>Edit</div>
                                <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                                <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div>
                                <div class='floatLbl' onclick='addFloatingNote(%s)'>&#10063;</div>
                                <div id='rem-%s' class='remLbl' onclick='removeNote(%s)'><span>&times;</span></div>
                            </div>
                            <div class='cardR siac-user-note' onmouseup='%s' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div>
                            <div id='tags-%s'  style='position: absolute; bottom: 0px; right: 0px;'>%s</div>
                            <div class='cardLeftBot' onclick='pycmd("siac-read-user-note %s")'>&nbsp;READ&nbsp;%s</div>
                        </div>"""

    def show_page(self, editor, page):
        """
            Results are paginated, this will display the results for the given page.
        """
        if self.lastResults is not None:
            self.print_search_results(self.lastResults, None, editor, False, self.last_had_timing_info, page, query_set = self.last_query_set)


    def print_search_results(self, db_list, stamp, editor=None, logging=False, printTimingInfo=False, page=1, query_set=None, is_queue=False, is_cached=False):
        """
        This is the html that gets rendered in the search results div.
        This will always print the first page.
        Args:
        db_list - a list of tuples, see SearchIndex.search()
        db_list.0: highlighted note text
        db_list.1: tags
        db_list.2: did
        db_list.3: nid
        db_list.4: score (not used currently)
        db_list.5: mid
        db_list.6: refs (not used currently)
        db_list.7: position in queue (only present if in queue)
        """
        if logging:
            log("Entering print_search_results")
            log("Length (searchResults): " + str(len(db_list)))
        if stamp is not None:
            if stamp != self.latest:
                return
        if not is_cached and not len(db_list) == 0:
            self.previous_calls.append([db_list, None, editor, logging, printTimingInfo, page, query_set, is_queue])
            if len(self.previous_calls) > 11:
                self.previous_calls.pop(0)

        html = ""
        allText = ""
        tags = []
        epochTime = int(time.time() * 1000)
        timeDiffString = ""
        newNote = ""
        lastNote = ""
        self.last_had_timing_info = printTimingInfo

        if db_list is not None and len(db_list) > 0:
            self.lastResults = db_list
            self.last_query_set = query_set

        searchResults = db_list[(page- 1) * 50: page * 50]
        nids = [r[3] for r in searchResults]

        if self.showRetentionScores:
            retsByNid = getRetentions(nids)
        ret = 0

        # various time stamps to collect information about rendering performance
        start = time.time()
        highlight_start = None
        build_user_note_start = None

        highlight_total = 0.0
        build_user_note_total = 0.0

        remaining_to_highlight = {}
        highlight_boundary = 15 if self.gridView else 10

        # for better performance, collect all notes that are .pdfs, and
        # query their reading progress after they have been rendered
        pdfs = []

        for counter, res in enumerate(searchResults):
            counter += (page - 1)* 50
            try:
                timeDiffString = self._getTimeDifferenceString(res[3], epochTime)
            except:
                if logging:
                    log("Failed to determine creation date: " + str(res[3]))
                timeDiffString = "Could not determine creation date"
            ret = retsByNid[int(res[3])] if self.showRetentionScores and int(res[3]) in retsByNid else None

            if ret is not None:
                retMark = "background: %s; color: black;" % (self._retToColor(ret))
                if str(res[3]) in self.edited:
                    retMark = ''.join((retMark, "max-width: 20px;"))
                retInfo = """<div class='retMark' style='%s'>%s</div>""" % (retMark, int(ret))
            else:
                retInfo = ""

            lastNote = newNote
            text = res[0]

            #non-anki notes should be displayed differently, we distinguish between title, text and source here
            build_user_note_start = time.time()
            if str(res[2]) == "-1":
                src = text.split("\u001f")[2]
                text = self._build_non_anki_note_html(text)
                if src.endswith(".pdf"):
                    pdfs.append(res[3])

            build_user_note_total += time.time() - build_user_note_start

            # hide fields that should not be shown
            if len(res) > 5 and str(res[5]) in self.fields_to_hide_in_results:
                text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in self.fields_to_hide_in_results[str(res[5])]])

            #remove double fields separators
            text = self._cleanFieldSeparators(text).replace("\\", "\\\\")

            #try to remove image occlusion fields
            text = self.try_hide_image_occlusion(text)

            #try to put fields that consist of a single image in their own line
            text = self.IMG_FLD.sub("|</span><br/>\\1<br/>\\2", text)

            #remove <div> tags if set in config
            if self.remove_divs:
                text = utility.text.remove_divs(text, " ")

            #highlight
            highlight_start = time.time()
            if query_set is not None:
                if counter - (page -1) * 50 < highlight_boundary:
                    text = self._mark_highlights(text, query_set)
                else:
                    remaining_to_highlight[res[3]] = ""
            highlight_total += time.time() - highlight_start

            if query_set is not None and counter - (page -1) * 50 >= highlight_boundary:
                remaining_to_highlight[res[3]] = text

            gridclass = "grid" if self.gridView else ""
            if self.gridView and len(text) < 200:
                if self.scale < 0.8:
                    gridclass = ' '.join((gridclass, "grid-smaller"))
                else:
                    gridclass = ' '.join((gridclass, "grid-small"))
            elif self.gridView and self.scale < 0.8:
                gridclass = ' '.join((gridclass, "grid-small"))

            elif self.gridView and len(text) > 700 and self.scale > 0.8:
                gridclass = ' '.join((gridclass, "grid-large"))

            if self.scale != 1.0:
                gridclass = ' '.join([gridclass, "siac-sc-%s" % str(self.scale).replace(".", "-")])

            # use either the template for addon's notes or the normal
            if str(res[2]) == "-1":
                newNote = self.noteTemplateUserNote % (gridclass, counter + 1, res[3], counter + 1,
                            "&nbsp;&#128336; " + timeDiffString,
                            "" if str(res[3]) not in self.edited else "&nbsp;&#128336; " + self._buildEditedInfo(self.edited[str(res[3])]),
                        retInfo, res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3], "getSelectionText()" if not is_queue else "", res[3], res[3], res[3], res[3],
                            text,
                            res[3], self.build_tag_string(res[1]), res[3], ": Q-%s&nbsp;" % (res[7] + 1) if len(res) >= 8 and res[7] is not None else "")
            else:
                newNote = self.noteTemplate % (gridclass, counter + 1, res[3], counter + 1,
                            "&nbsp;&#128336; " + timeDiffString,
                            "" if str(res[3]) not in self.edited else "&nbsp;&#128336; " + self._buildEditedInfo(self.edited[str(res[3])]),
                            retInfo, res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3],
                            text,
                            res[3], self.build_tag_string(res[1]), res[3])
            # if self.gridView:
            #     if counter % 2 == 1:
            #         html += "<div class='gridRow'>%s</div>" % (lastNote + newNote)
            #     elif counter == len(searchResults) - 1:
            #         html += "<div class='gridRow'>%s</div>" % (newNote)
            # else:
            html = f"{html}{newNote}"
            tags = self._addToTags(tags, res[1])
            if counter - (page - 1) * 50 < 20:
                allText = f"{allText} {res[0][:5000]}"
        tags.sort()
        html = html.replace("`", "&#96;").replace("$", "&#36;")
        pageMax = math.ceil(len(db_list) / 50.0)
        if get_index() is not None and get_index().lastResDict is not None:
            get_index().lastResDict["time-html"] = int((time.time() - start) * 1000)
            get_index().lastResDict["time-html-highlighting"] = int(highlight_total * 1000)
            get_index().lastResDict["time-html-build-user-note"] = int(build_user_note_total * 1000)
        if stamp is None and self.last_took is not None:
            took = self.last_took
            stamp = -1
        elif stamp is not None:
            took = utility.misc.get_milisec_stamp() - stamp
            self.last_took = took
        else:
            took = "?"

        if not self.hideSidebar:
            infoMap = {
                "Took" :  "<b>%s</b> ms %s" % (took, "&nbsp;<b style='cursor: pointer' onclick='pycmd(`lastTiming`)'>&#9432;</b>" if printTimingInfo else ""),
                "Found" :  "<b>%s</b> notes" % (len(db_list) if len(db_list) > 0 else "<span style='color: red;'>0</span>")
            }
            timing = "true" if printTimingInfo else "false"
            info = self.build_info_table(infoMap, tags, allText)
            cmd = "setSearchResults(`%s`, `%s`, %s, page=%s, pageMax=%s, total=%s, cacheSize=%s, stamp=%s, printTiming=%s);" % (html, info[0].replace("`", "&#96;"), json.dumps(info[1]), page, pageMax, len(db_list), len(self.previous_calls), stamp, timing)
        else:
            cmd = "setSearchResults(`%s`, ``, null, page=%s , pageMax=%s, total=%s, cacheSize=%s, stamp=%s, printTiming=%s);" % (html, page, pageMax, len(db_list), len(self.previous_calls), stamp, timing)
        cmd = f"{cmd}updateSwitchBtn({len(searchResults)});" 

        self._js(cmd, editor)

        if len(remaining_to_highlight) > 0:
            cmd = ""
            for nid,text in remaining_to_highlight.items():
                cmd = ''.join((cmd, "document.getElementById('%s').innerHTML = `%s`;" % (nid, self._mark_highlights(text, query_set))))
            self._js(cmd, editor)

        if len(pdfs) > 0:
            pdf_info_list = get_pdf_info(pdfs)

            if pdf_info_list is not None and len(pdf_info_list) > 0:
                cmd = ""
                for i in pdf_info_list:
                    perc = int(i[1] * 10.0 / i[2])
                    prog_bar = ""
                    for x in range(0, 10):
                        if x < perc:
                            prog_bar = ''.join((prog_bar, "<div class='siac-prog-sq-filled'></div>"))
                        else:
                            prog_bar = ''.join((prog_bar, "<div class='siac-prog-sq'></div>"))
                    cmd = ''.join((cmd, "document.querySelector('[id=\"%s\"] .siac-prog-tmp').innerHTML = `%s &nbsp;%s / %s`;" % (i[0], prog_bar, i[1], i[2])))
                self._js(cmd, editor)
            
        return (highlight_total * 1000, build_user_note_total)


    def js(self, js):
        """
            Use webview's eval function to execute the given js.
        """
        if self.editor is None or self.editor.web is None:
            return
        self.editor.web.eval(js)

    def _js(self, js, editor):
        """
            Try to eval the given js, prefer if editor ref is given (through cmd parsing).
        """
        if editor is None or editor.web is None:
            if self.editor is not None and self.editor.web is not None:
                self.editor.web.eval(js)
        else:
            editor.web.eval(js)

    def build_tag_string(self, tags, hover = True, maxLength = -1, maxCount = -1):
        """
        Builds the html for the tags that are displayed at the bottom right of each rendered search result.
        """
        html = ""
        tags_split = tags.split()
        tm = self.getTagMap(tags_split)
        totalLength = sum([len(k) for k,v in tm.items()])
        if maxLength == -1:
            maxLength = 40 if not self.gridView else 30
        if maxCount == -1:
            maxCount = 3 if not self.gridView else 2
        if len(tm) <= maxCount or totalLength < maxLength:
            hover = "onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'" if hover else ""
            for t, s in tm.items():
                stamp = "siac-tg-" + utility.text.get_stamp()
                if len(s) > 0:
                    tagData = " ".join(self.iterateTagmap({t : s}, ""))
                    if len(s) == 1 and tagData.count("::") < 2 and not t in tags_split:
                        html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData.split(' ')[1]}' {hover} onclick='tagClick(this);'>{utility.text.trim_if_longer_than(tagData.split(' ')[1], maxLength)}</div>"
                    else:
                        html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData}' {hover} onclick='tagClick(this);'>{utility.text.trim_if_longer_than(t, maxLength)} (+{len(s)})</div>" 
                else:
                    html = f"{html}<div class='tagLbl' data-stamp='{stamp}' {hover} data-name='{t}' onclick='tagClick(this);'>{utility.text.trim_if_longer_than(t, maxLength)}</div>"
        else:
            stamp = "siac-tg-" + utility.text.get_stamp()
            tagData = " ".join(self.iterateTagmap(tm, ""))
            html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData}' onclick='tagClick(this);'>{len(tm)} tags ...</div>" 

        return html


    def sortByDate(self, mode):
        """
            Rerenders the last search results, but sorted by creation date.
        """
        if self.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        self.latest = stamp
        sortedByDate = list(sorted(self.lastResults, key=lambda x: x[3]))
        if mode == "desc":
            sortedByDate = list(reversed(sortedByDate))
        self.print_search_results(sortedByDate, stamp)


    def removeUntagged(self):
        if self.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        self.latest = stamp
        filtered = []
        for r in self.lastResults:
            if r[1] is None or len(r[1]) == 0:
                continue
            filtered.append(r)
        self.print_search_results(filtered, stamp)

    def removeTagged(self):
        if self.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        self.latest = stamp
        filtered = []
        for r in self.lastResults:
            if r[1] is None or len(r[1]) == 0:
                filtered.append(r)
        self.print_search_results(filtered, stamp)

    def removeUnreviewed(self):
        if self.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        self.latest = stamp
        filtered = []
        nids = []
        for r in self.lastResults:
            nids.append(str(r[3]))
        nidStr =  "(%s)" % ",".join(nids)
        unreviewed = [r[0] for r in mw.col.db.execute("select nid from cards where nid in %s and reps = 0" % nidStr).fetchall()]
        for r in self.lastResults:
            if int(r[3]) not in unreviewed:
                filtered.append(r)
        self.print_search_results(filtered, stamp)

    def removeReviewed(self):
        if self.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        self.latest = stamp
        filtered = []
        nids = []
        for r in self.lastResults:
            nids.append(str(r[3]))
        nidStr =  "(%s)" % ",".join(nids)
        reviewed = [r[0] for r in mw.col.db.execute("select nid from cards where nid in %s and reps > 0" % nidStr).fetchall()]
        for r in self.lastResults:
            if int(r[3]) not in reviewed:
                filtered.append(r)
        self.print_search_results(filtered, stamp)

    def _build_non_anki_note_html(self, text):
        """
        User's notes should be displayed in a way to visually distinguish between title, text and source.
        Also, text might need to be cut if is too long to reduce time needed for highlighting, extracting keywords, and rendering.
        """
        #trim very long texts:
        if len(text) > 5000:
            src_begin_index = text.rfind("\u001f")
            src = text[src_begin_index + 1:]
            title = text[:text.find("\u001f")]
            body = text[text.find("\u001f") +1:src_begin_index][:5000]
            #there might be unclosed tags now, but parsing would be too much overhead, so simply remove div, a and span tags
            #there might be still problems with <p style='...'>
            body = utility.text.remove_tags(body, ["div", "span", "a"])
            last_open_bracket = body.rfind("<")
            if last_open_bracket >= len(body) - 500 or body.rfind(" ") < len(body) - 500:
                last_close_bracket = body.rfind(">")
                if last_close_bracket < last_open_bracket:
                    body = body[:last_open_bracket]
            body += "<br></ul></b></i></em></span></p></p><p style='text-align: center; user-select: none;'><b>(Text was cut - too long to display)</b></p>"
        else:
            title = text.split("\u001f")[0]
            body = text.split("\u001f")[1]
            src = text.split("\u001f")[2]
        is_pdf = src is not None and src.lower().strip().endswith(".pdf")
        title = "%s<b>%s</b>%s" % ("<span class='siac-pdf-icon'></span>" if is_pdf else "", title if len(title) > 0 else "Unnamed Note", "<hr style='margin-bottom: 5px; border-top: dotted 2px;'>" if len(body.strip()) > 0 else "")
        if src is not None and len(src) > 0:
            src = "<br/><hr style='border-top: dotted 2px;'><i>Source: %s</i>" % (src)
        else:
            src = ""
        if is_pdf:
            p_html = "<div class='siac-prog-sq'></div>" * 10
            prog_bar = f"<div class='siac-prog-tmp'>{p_html} &nbsp;0 / ?</div>"
        else:
            prog_bar = ""
        return title + body + src + prog_bar


    def _buildEditedInfo(self, timestamp):
        diffInSeconds = time.time() - timestamp
        if diffInSeconds < 60:
            return "Edited just now"
        if diffInSeconds < 120:
            return "Edited 1 minute ago"
        if diffInSeconds < 3600:
            return "Edited %s minutes ago" % int(diffInSeconds / 60)
        return "Edited today"

    def _getTimeDifferenceString(self, nid, now):
        """
            Helper function that builds the string that is displayed when clicking on the result number of a note.
        """
        diffInMinutes = (now - int(nid)) / 1000 / 60
        diffInDays = diffInMinutes / 60 / 24

        if diffInDays < 1:
            if diffInMinutes < 2:
                return "Created just now"
            if diffInMinutes < 60:
                return "Created %s minutes ago" % int(diffInMinutes)
            return "Created %s hours ago" % int(diffInMinutes / 60)


        if diffInDays >= 1 and diffInDays < 2:
            return "Created yesterday"
        if diffInDays >= 2:
            return "Created %s days ago" % int(diffInDays)
        return ""


    def build_info_table(self, infoMap, tags, allText):
        infoStr = "<table>"
        for key, value in infoMap.items():
            infoStr =f"{infoStr}<tr><td>{key}</td><td id='info-{key}'>{value}</td></tr>"
        infoStr = f"{infoStr}</table><div class='searchInfoTagSep'><span class='tag-symbol'>&#9750;</span>&nbsp;Tags:</div><div id='tagContainer' style='max-height: 180px; overflow-y: auto;'>"
        tagStr = ""
        if len(tags) == 0:
            infoStr += "No tags in the results."
            infoMap["Tags"] = "No tags in the results."
        else:
            for key, value in self.getTagMap(tags).items():
                stamp = f"siac-tg-{utility.text.get_stamp()}"
                if len(value)  == 0:
                    tagStr = f"{tagStr}<span class='tagLbl' data-stamp='{stamp}' data-name='{key}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(key, 19)}</span>"
                else:
                    tagData = " ".join(self.iterateTagmap({key : value}, ""))
                    if len(value) == 1 and tagData.count("::") < 2 and not key in tags:
                        tagStr = f"{tagStr}<span class='tagLbl' data-stamp='{stamp}' data-name='{tagData.split(' ')[1]}' data-tags='{tagData}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(tagData.split()[1],16)}</span>"
                    else:
                        tagStr = f"<span class='tagLbl' data-stamp='{stamp}' data-name='{tagData}' data-tags='{tagData}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(key,12)}&nbsp; (+{len(value)})</span>"

            infoStr += tagStr
            infoMap["Tags"] = tagStr

        infoStr = f"{infoStr}</div><div class='searchInfoTagSep bottom' >Keywords:</div><div id='keywordContainer'>"
        mostCommonWords = self._most_common_words(allText)
        infoStr = f"{infoStr}{mostCommonWords}</div>"
        infoMap["Keywords"] = mostCommonWords
        return (infoStr, infoMap)
    

    def _cleanFieldSeparators(self, text):
        text = self.SEP_RE.sub("\u001f", text)
        if text.endswith("\u001f"):
            text = text[:-1]
        text = text.replace("\u001f", "<span class='fldSep'>|</span>")
        return text

    def try_hide_image_occlusion(self, text):
        """
        Image occlusion cards take up too much space, so we try to hide all images except for the first.
        """
        if not text.count("<img ") > 1:
            return text
        text = self.IO_REPLACE.sub("(IO - image hidden)", text)
        return text


    def _most_common_words(self, text):
        """
        Returns the html that is displayed in the right sidebar containing the clickable keywords.
        """
        if text is None or len(text) == 0:
            return "No keywords for empty result."
        text = utility.text.clean(text, self.stopwords)
        counts = {}
        for token in text.split():
            if token == "" or len(token) == 1 or self.SOUND_TAG.match(token):
                continue
            if token.lower() in counts:
                counts[token.lower()][1] += 1
            else:
                counts[token.lower()] = [token, 1]
        sortedCounts = sorted(counts.items(), key=lambda kv: kv[1][1], reverse=True)
        html = ""
        for entry in sortedCounts[:15]:
            html = "%s<a class='keyword' href='#' onclick='event.preventDefault(); searchFor($(this).text())'>%s</a>, " % (html, entry[1][0])
        if len(html) == 0:
            return "No keywords for empty result."
        return html[:-2]

    def get_result_html_simple(self, db_list, tag_hover = True, search_on_selection = True):
        html = ""
        epochTime = int(time.time() * 1000)
        timeDiffString = ""
        newNote = ""
        lastNote = ""
        nids = [r[3] for r in db_list]
        if self.showRetentionScores:
            retsByNid = getRetentions(nids)
        ret = 0
        for counter, res in enumerate(db_list):
            try:
                timeDiffString = self._getTimeDifferenceString(res[3], epochTime)
            except:
                timeDiffString = "Could not determine creation date"
            ret = retsByNid[int(res[3])] if self.showRetentionScores and int(res[3]) in retsByNid else None

            if ret is not None:
                retMark = "background: %s; color: black;" % (self._retToColor(ret))
                if str(res[3]) in self.edited:
                    retMark += "max-width: 20px;"
                retInfo = """<div class='retMark' style='%s'>%s</div>
                                """ % (retMark, int(ret))
            else:
                retInfo = ""

            lastNote = newNote
            text = res[0]

            #non-anki notes should be displayed differently, we distinguish between title, text and source here
            if str(res[2]) == "-1":
                text = self._build_non_anki_note_html(text)

            # hide fields that should not be shown
            if len(res) > 5 and str(res[5]) in self.fields_to_hide_in_results:
                text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in self.fields_to_hide_in_results[str(res[5])]])


            #remove <div> tags if set in config
            if self.remove_divs:
                text = utility.text.remove_divs(text)

            text = self._cleanFieldSeparators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
            text = self.try_hide_image_occlusion(text)
            #try to put fields that consist of a single image in their own line
            text = self.IMG_FLD.sub("|</span><br/>\\1<br/>\\2", text)
            template = self.noteTemplateSimple if str(res[2]) != "-1" else self.noteTemplateUserNoteSimple
            newNote = template % ( counter + 1,
                        "&nbsp;&#128336; " + timeDiffString,
                        "" if str(res[3]) not in self.edited else "&nbsp;&#128336; " + self._buildEditedInfo(self.edited[str(res[3])]),
                        retInfo, res[3],res[3],"getSelectionText()" if search_on_selection else "", res[3],res[3],
                        text,
                        self.build_tag_string(res[1], tag_hover, maxLength = 25, maxCount = 2), res[3])

            html += newNote
        return html


    def print_timeline_info(self, context_html, db_list):
        html = self.get_result_html_simple(db_list, tag_hover= False)

        if len(html) == 0:
            html = "%s <div style='text-align: center; line-height: 100px;'>No notes added on that day.</div><div style='text-align: center;'> Tip: Hold Ctrl and hover over the timeline for faster navigation</div>" % (context_html)
        else:
            html = """
                %s
                <div id='cal-info-notes' style='overflow-y: auto; height: 190px; margin: 10px 0 5px 0; padding-left: 4px; padding-right: 8px;'>%s</div>
            """ % (context_html, html)
        self.editor.web.eval("document.getElementById('cal-info').innerHTML = `%s`;" % html)


    def showInModal(self, text):
        cmd = "$('#a-modal').show(); document.getElementById('modalText').innerHTML = `%s`;" % text
        self.js(cmd)


    def show_in_large_modal(self, html):
        js = """
            $('#siac-reading-modal').html(`%s`);
            document.getElementById('siac-reading-modal').style.display = 'flex';

        """ % html.replace("`", "&#96;")
        self.js(js) 

    def empty_result(self, message):
        if self.editor is None or self.editor.web is None:
            return
        self.editor.web.eval("setSearchResults('', `%s`, null, 1, 1, 50, %s)" % (message, len(self.previous_calls) + 1))

    def _loadPlotJsIfNotLoaded(self):
        if not self.plotjsLoaded:
            with open(utility.misc.get_web_folder_path() + "plot.js") as f:
                plotjs = f.read()
            self.editor.web.eval(plotjs)
            self.plotjsLoaded = True


    def show_search_modal(self, on_enter_attr, header):
        self.editor.web.eval("""
        document.getElementById('siac-search-modal').style.display = 'block';
        document.getElementById('siac-search-modal-header').innerHTML = `%s`;
        document.getElementById('siac-search-modal-inp').setAttribute('onkeyup', '%s');
        document.getElementById('siac-search-modal-inp').focus();
        """ % (header,on_enter_attr))

    def showStats(self, text, reviewPlotData, ivlPlotData, timePlotData):

        self._loadPlotJsIfNotLoaded()

        cmd = "$('#a-modal').show(); document.getElementById('modalText').innerHTML = `%s`; document.getElementById('modalText').scrollTop = 0; " % (text)
        c = 0
        for k,v in reviewPlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: {
                            lines: { show: true, fillColor: "#2496dc" },
                            points: { show: true, fillColor: "#2496dc" }
                    },
                    label: "Ease",
                    yaxis: { max: 5, min: 0, ticks: [[0, ''], [1, 'Failed'], [2, 'Hard'], [3, 'Good'], [4, 'Easy']],
                                tickFormatter: function (v, axis) {
                                if (v == 1) {
                                    $(this).css("color", "red");
                                }
                                return v;
                                }
                    } ,
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"]
                    }

                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)
        for k,v in ivlPlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: {
                            lines: { show: true, fillColor: "#2496dc" },
                            points: { show: true, fillColor: "#2496dc" }
                    },
                    label: "Interval",
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"]
                    }

                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)

        for k,v in timePlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: {
                            lines: { show: true, fillColor: "#2496dc" },
                            points: { show: true, fillColor: "#2496dc" }
                    },
                    label: "Answer Time",
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"]
                    }

                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)

        self.js(cmd)

    def hideModal(self):
        self.js("$('#a-modal').hide();")

    def _addToTags(self, tags, tagStr):
        if tagStr == "":
            return tags
        for tag in tagStr.split(" "):
            if tag == "":
                continue
            if tag in tags:
                continue
            tags.append(tag)
        return tags

    def printTagHierarchy(self, tags):
        cmd = """document.getElementById('modalText').innerHTML = `%s`;
        $('.tag-list-item').click(function(e) {
            e.stopPropagation();
            let icn = $(this).find('.tag-btn').first();
            let text = icn.text();
            if (text.endsWith(']')) {
                if (text.endsWith('[+]'))
                    icn.text(text.substring(0, text.length - 3) + '[-]');
                else
                    icn.text(text.substring(0, text.length - 3) + '[+]');
            }
            $(this).children('ul').toggle();
        });

        """ % self.buildTagHierarchy(tags)
        self.js(cmd)

    def buildTagHierarchy(self, tags):
        tmap = self.getTagMap(tags)
        config = mw.addonManager.getConfig(__name__)
        def iterateMap(tmap, prefix, start=False):
            if start:
                html = "<ul class='tag-list outer'>"
            else:
                html = "<ul class='tag-list'>"
            for key, value in tmap.items():
                full = prefix + "::" + key if prefix else key
                html += "<li class='tag-list-item'><span class='tag-btn'>%s %s</span><div class='tag-add' data-name=\"%s\" data-target='%s' onclick='event.stopPropagation(); tagClick(this)'>%s</div>%s</li>" % (
                    utility.text.trim_if_longer_than(key, 25),
                    "[-]" if value else "" ,
                    utility.text.delete_chars(full, ["'", '"', "\n", "\r\n", "\t", "\\"]),
                    key,
                    "+" if not config["tagClickShouldSearch"] else "<div class='siac-btn-small'>Search</div>",
                iterateMap(value, full))
            html += "</ul>"
            return html

        html = iterateMap(tmap, "", True)
        return html

    def getTagMap(self, tags):
        return utility.tags.to_tag_hierarchy(tags)

    def iterateTagmap(self, tmap, prefix):
        if len(tmap) == 0:
            return []
        res = []
        if prefix:
            prefix = prefix + "::"
        for key, value in tmap.items():
            if type(value) is dict:
                if len(value) > 0:
                    res.append(prefix + key)
                    res +=  self.iterateTagmap(value, prefix + key)
                else:
                    res.append(prefix + key)
        return res

    def updateSingle(self, note):
        """
        Used after note has been edited. The edited note should be rerendered.
        To keep things simple, only note text and tags are replaced.
        """
        if self.editor is None or self.editor.web is None:
            return
        tags = note[2]
        tagStr =  self.build_tag_string(tags)
        nid = note[0]
        text = note[1]

        # hide fields that should not be shown
        if len(note) > 4 and str(note[4]) in self.fields_to_hide_in_results:
            text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in self.fields_to_hide_in_results[str(note[4])]])

        text = self._cleanFieldSeparators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
        text = self.try_hide_image_occlusion(text)
        text = self.IMG_FLD.sub("|</span><br/>\\1<br/>\\2", text)

        #find rendered note and replace text and tags
        self.editor.web.eval("""
            document.getElementById('%s').innerHTML = `%s`;
            document.getElementById('tags-%s').innerHTML = `%s`;
        """ % (nid, text, nid, tagStr))

        self.editor.web.eval("$('#cW-%s').find('.rankingLblAddInfo').hide();" % nid)
        self.editor.web.eval("fixRetMarkWidth(document.getElementById('cW-%s'));" % nid)
        self.editor.web.eval("$('#cW-%s .editedStamp').html(`&nbsp;&#128336; Edited just now`).show();" % nid)

    def _mark_highlights(self, text, querySet):

        currentWord = ""
        currentWordNormalized = ""
        textMarked = ""
        lastIsMarked = False
        # c = 0
        for char in text:
            # c += 1
            if self.wordToken.match(char):
                currentWordNormalized = ''.join((currentWordNormalized, utility.text.ascii_fold_char(char).lower()))
                # currentWordNormalized = ''.join((currentWordNormalized, char.lower()))
                if utility.text.is_chinese_char(char) and str(char) in querySet:
                    currentWord = ''.join((currentWord, "<MARK>%s</MARK>" % char))
                else:
                    currentWord = ''.join((currentWord, char))

            else:
                #we have reached a word boundary
                #check if word is empty
                if currentWord == "":
                    textMarked = ''.join((textMarked, char))
                else:
                    #if the word before the word boundary is in the query, we want to highlight it
                    if currentWordNormalized in querySet:
                        #we check if the word before has been marked too, if so, we want to enclose both, the current word and
                        # the word before in the same <mark></mark> tag (looks better)
                        if lastIsMarked and not "\u001f" in textMarked[textMarked.rfind("<MARK>"):]:
                        # if lastIsMarked:
                            closing_index = textMarked.rfind("</MARK>")
                            textMarked = ''.join((textMarked[0: closing_index], textMarked[closing_index + 7 :]))
                            textMarked = ''.join((textMarked, currentWord, "</MARK>", char))
                        else:
                            textMarked = ''.join((textMarked, "<MARK>", currentWord, "</MARK>", char))
                            # c += 13
                        lastIsMarked = True
                    #if the word is not in the query, we simply append it unhighlighted
                    else:
                        textMarked = ''.join((textMarked, currentWord, char))
                        lastIsMarked = False
                    currentWord = ""
                    currentWordNormalized = ""
        if currentWord != "":
            if currentWord != "MARK" and currentWordNormalized in querySet:
                textMarked = ''.join((textMarked, "<MARK>", currentWord, "</MARK>"))
            else:
                textMarked = ''.join((textMarked, currentWord))

        return textMarked

    def show_tooltip(self, text):
        if mw.addonManager.getConfig(__name__)["hideSidebar"]:
            tooltip("Query was empty after cleaning.")

    def show_in_modal_subpage(self, html):
        self.js("showModalSubpage(`%s`);" % html)


    def print_pdf_search_results(self, results, stamp, query_set):
        clz_btn_js = """
                if ($('#siac-pdf-tooltip').data('sentences').length === 0) {
                    $('#siac-cloze-btn,#siac-tt-web-btn').hide();
                } else {
                    $('#siac-cloze-btn').text(`Generate Clozes (${$('#siac-pdf-tooltip').data('sentences').length})`);
                }
        """
        if results is not None and len(results) > 0:
            html = self.get_result_html_simple(results[:50], False, False)
            qhtml = """
                <div id='siac-tooltip-center' onclick='centerTooltip();'></div>
                <div class='siac-search-icn-dark' id='siac-tt-web-btn' onclick='pycmd("siac-show-web-search-tooltip " + $("#siac-pdf-tooltip").data("selection"));'></div>
                    <span id='siac-cloze-btn' onclick='sendClozes();'>Generate Clozes</span>
                <div style='width: calc(100%%- 18px); padding-left: 9px; padding-right: 9px; text-align: center; margin: 8px 0 8px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                    <i>%s</i>
                </div>
            """ % (" ".join(query_set))
            self.editor.web.eval("""
                document.getElementById('siac-pdf-tooltip-results-area').innerHTML = `%s`
                document.getElementById('siac-pdf-tooltip-results-area').scrollTop = 0; 
                document.getElementById('siac-pdf-tooltip-top').innerHTML = `%s`
                document.getElementById('siac-pdf-tooltip-bottom').innerHTML = ``;
                document.getElementById('siac-pdf-tooltip-searchbar').style.display = "inline-block";

            %s
            """ % (html, qhtml, clz_btn_js))
        else:
            if query_set is None or len(query_set)  == 0:
                message = "Query was empty after cleaning."
            else:
                message = "Nothing found for query: <br/><br/><i>%s</i>" % (utility.text.trim_if_longer_than(" ".join(query_set), 200))
            self.editor.web.eval("""
                document.getElementById('siac-pdf-tooltip-results-area').innerHTML = `%s`
                document.getElementById('siac-pdf-tooltip-top').innerHTML = `<div id='siac-tooltip-center' onclick='centerTooltip();'></div>
                                                        <div class='siac-search-icn-dark' id='siac-tt-web-btn' onclick='pycmd("siac-show-web-search-tooltip " + $("#siac-pdf-tooltip").data("selection"));'></div>
                                                            <span id='siac-cloze-btn' onclick='sendClozes();'>Generate Clozes</span>
                                                            <br><br>`;
                document.getElementById('siac-pdf-tooltip-bottom').innerHTML = ``;
                document.getElementById('siac-pdf-tooltip-searchbar').style.display = "inline-block";
                %s
            """ % (message, clz_btn_js))



    @staticmethod
    def _retToColor(retention):
        if retention < (100 / 7.0):
            return "#ff0000"
        if retention < (100 / 7.0) * 2:
            return "#ff4c00"
        if retention < (100 / 7.0) * 3:
            return "#ff9900"
        if retention < (100 / 7.0) * 4:
            return "#ffe500"
        if retention < (100 / 7.0) * 5:
            return "#cbff00"
        if retention < (100 / 7.0) * 6:
            return "#7fff00"
        return "#32ff00"


