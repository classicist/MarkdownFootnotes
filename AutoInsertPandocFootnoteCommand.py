#!/usr/bin/python
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
import re

class AutoInsertPandocFootnoteCommand(sublime_plugin.TextCommand):
  LABEL_PATTERN = "\[\^\d+\](?!(\:))"
  ENTRY_PATTERN = "^\[\^\d+\]\:"

  def previous_note_label(self, cursor_region):
    last_note_label = "[^0]"
    note_label_region = sublime.Region(0, cursor_region.end())
    text = self.view.substr(note_label_region)
    matchs = re.findall("(\[\^\d+\])(?!\:)", text)
    if matchs:
      last_note_label = matchs[-1]

    return(last_note_label)

  def note_label(self, cursor_region):
    note_label_region = self.view.find(self.LABEL_PATTERN, cursor_region.begin())
    return(self.view.substr(note_label_region))

  def increment_fn(self, note_label):
    if not re.match(self.LABEL_PATTERN, note_label):
      note_label = "[^0]"
    note_number = re.findall(r'\d+', note_label)[0]
    note_number =  int(note_number) + 1
    note_label = "[^%(note_number)s]" % locals()
    return(note_label)

  def move_cursor(self, region):
    next_region = region
    next_region.a = region.a + 1
    next_region.b = region.b + 1
    return(next_region)

  def insert_new_note(self, edit):
    label_cursor_region = self.view.sel()[0]
    last_note_label = self.previous_note_label(label_cursor_region)
    new_note_lable  = self.increment_fn(last_note_label)
    self.view.insert(edit, label_cursor_region.end(), new_note_lable)
    label_cursor_region = self.move_cursor(label_cursor_region)
    return(label_cursor_region)

  def entry_for_label(self, note_label):
    label_number = re.findall(r'\d+', note_label)[0]
    entry_pattern = "^\[\^%(label_number)s\]:" % locals()
    entry_region = self.view.find(entry_pattern, 0) #assuming there is only one entry bc this will always find the first
    entry = self.view.substr(entry_region)
    return({'entry': entry, 'region': entry_region})

  def eof_region(self):
    eof_region = self.view.find_all(".\Z")
    if eof_region is None:
      eof_region = sublime.Region(-1,-1)
    else:
      eof_region = eof_region[0]
    return(eof_region)

  def get_entry_text(self, type, text, label_cursor_region):
    # label_cursor_region is used by subclass
    entry_text = ""
    if type == "new":
        entry_text = "\n\n%(text)s" % locals()
    if type == "first_or_middle":
        entry_text = "%(text)s\n\n" % locals()
    if type == "last":
        entry_text = "\n\n%(text)s" % locals()
    return(entry_text)

  def insert_new_entry(self, edit, label_cursor_region):
    label_before_previous_label = self.previous_note_label(label_cursor_region)
    previous_label = self.increment_fn(label_before_previous_label)
    entry = self.entry_for_label(previous_label)
    raw_entry = entry['entry']
    is_first_or_middle_position_entry = (raw_entry != "")
    entries_exist = len(self.view.find_all(self.ENTRY_PATTERN)) > 0

    if entries_exist:
      if is_first_or_middle_position_entry:
        entry_text = self.get_entry_text("first_or_middle", raw_entry, label_cursor_region)
        entry_spot = entry['region'].begin()
        entry_cursor_region = entry['region']
        self.view.insert(edit, entry_spot, entry_text)
      else: #is last entry in the file
        previous_region = self.view.full_line(self.view.find_all(self.ENTRY_PATTERN)[-1])
        entry_spot = previous_region.end()
        previous_entry = self.view.substr(previous_region)
        new_entry = re.sub("\:.*", ":", previous_entry)
        incremented_entry_number = int(re.findall(r'\d+', new_entry)[0]) + 1
        entry_text = re.sub('\d+', str(incremented_entry_number), new_entry)
        entry_text = self.get_entry_text("last", entry_text, label_cursor_region)
        self.view.insert(edit, entry_spot, entry_text)
        new_region = self.view.find_all(self.ENTRY_PATTERN)[-1]
        entry_cursor_region = new_region
    else: #no entries exist in the file yet, this is the first
      entry_text = self.get_entry_text("new", "[^1]:", label_cursor_region)
      entry_spot = self.eof_region().end()
      self.view.insert(edit, entry_spot, entry_text)
      entry_cursor_region = self.eof_region()

    return(entry_cursor_region)

  def consecutize_numbering(self, edit, note_type = "label"):
    if note_type == "label":
      note_pattern  = "(\[\^\d+\])(?!\:)"
    else:
      note_pattern  = "(\[\^\d+\]\:)"

    #lesson learned: do not iterative string modifications in the buffer. Just grab
    #the whole buffer, do your mods in python, then replace the whole buffer.
    buffer_contents =  self.view.substr(sublime.Region(0, self.view.size()))
    labels = re.findall(note_pattern, buffer_contents)

    count = 1
    new_buff = ""
    old_index = 0

    for old_label in labels:
      left = buffer_contents.find(old_label)
      index = left + len(old_label)
      new_label = re.sub(r'\d+', str(count), old_label)
      buffer_contents = re.sub(re.escape(old_label), new_label, buffer_contents, 1)
      updated_slice   = buffer_contents[0:index]
      buffer_contents = buffer_contents[index:] #chop off searched buffer
      new_buff = new_buff + updated_slice
      count = count + 1

    new_buff = new_buff + buffer_contents #add back unsearched buffer
    self.view.erase(edit, sublime.Region(0, self.view.size()))
    self.view.insert(edit, 0, new_buff)

  def move_cursor_to_region_at_EOL(self, region):
    # Clear the cursor's position and move it to `region`.
    region = self.view.line(region) # b is now EOL
    region.a = region.b
    cursor = self.view.sel()
    self.original_position = cursor[0]
    cursor.clear()
    cursor.add(region)
    self.view.show(region)

  def ensure_same_number_of_labels_and_entries(self):
    label_regions = self.view.find_all(self.LABEL_PATTERN)
    entry_regions = self.view.find_all(self.ENTRY_PATTERN)
    if len(label_regions) != len(entry_regions):
      no_of_labels  = len(label_regions)
      no_of_entries = len(entry_regions)
      sublime.error_message("Some footnotes don't have a body: There are %(no_of_labels)s footnotes in the text and %(no_of_entries)s footnotes in the footer." % locals())
      return(False)
    else:
      return(True)

  def ensure_note_and_entries_match(self):
    #invariant = there are the same number of notes as there are entries
    #invariant = the number of notes and bodies may be 0
    label_regions = self.view.find_all(self.LABEL_PATTERN)
    entry_regions = self.view.find_all(self.ENTRY_PATTERN)
    index = 0
    for region in label_regions:
      label = self.view.substr(region)
      entry = self.view.substr(entry_regions[index])
      if re.match(re.escape(label), entry) is None:
        sublime.error_message("Footnote %(label)s has no body. Please add a corresponding body in the footer before you add another note." % locals())
        return(False)
      index = index + 1
    return(True)

  def run(self, edit):
    proceed = False

    proceed = self.ensure_same_number_of_labels_and_entries()
    if not proceed:
      return
    proceed = self.ensure_note_and_entries_match()
    if not proceed:
      return
    label_cursor_region = self.insert_new_note(edit)
    entry_cursor_region = self.insert_new_entry(edit, label_cursor_region)
    self.consecutize_numbering(edit, "label")
    self.consecutize_numbering(edit, "entry")
    self.move_cursor_to_region_at_EOL(entry_cursor_region)


######################################################################################
######################################################################################
######################################################################################

class AutoInsertPandocFootnoteWithPositionCommand(AutoInsertPandocFootnoteCommand):
  def run(self, edit):
    AutoInsertPandocFootnoteCommand.run(self, edit)

  def get_entry_text(self, type, text, label_cursor_region):
    text = AutoInsertPandocFootnoteCommand.get_entry_text(self,type, text, label_cursor_region)
    if label_cursor_region.begin() == label_cursor_region.end():
      return(text) #if there is no highlighted region, do nothing

    paragraph_text   = self.get_paragraph_containing_cursor(label_cursor_region)
    highlighted_text = self.get_text_in_highlighted_region(label_cursor_region)
    pos              = self.get_start_and_end_position(paragraph_text, highlighted_text)

    text = text.rstrip() + pos + "\n\n"
    return(text)

  def find_beginning_of_paragraph(self, start):
    r = sublime.Region(0, start)
    lines = self.view.split_by_newlines(r)
    lines.reverse() #search backward from start
    last_str = u''
    stop_line = sublime.Region(0,0)

    index = 0
    for line in lines:
      on_last_line = (len(lines) - 1) == index
      if on_last_line: #if we are on the last line, there were no matches
        return(stop_line)
      else:
        next_line = lines[index + 1]
        index     = index + 1

      current_str = self.view.substr(line)
      next_str = self.view.substr(next_line)

      current_line_has_text = not re.match("\A\s*\Z", current_str)
      next_line_is_empty    = not not re.match("\A\s*\Z", next_str)

      if (current_line_has_text and next_line_is_empty):
        stop_line = line
        break

    return stop_line

  def get_paragraph_containing_cursor(self, label_cursor_region):
    first_line_region = self.find_beginning_of_paragraph( label_cursor_region.end() )
    paragraph_region = sublime.Region(first_line_region.begin(), label_cursor_region.end())
    paragraph_text = self.view.substr(paragraph_region)
    paragraph_text = self.cleanup_paragraph_text(paragraph_text)
    return(paragraph_text)

  def cleanup_paragraph_text(self, paragraph_text):
    paragraph_start_pattern  = "(\n\n|\A)__(\d+|\.|praef|pref)+__\s*"
    paragraph_text = re.sub(paragraph_start_pattern, "", paragraph_text) #clip off intro matter
    paragraph_text = paragraph_text.strip()
    paragraph_text = re.sub("\n", " ", paragraph_text)
    paragraph_text = re.sub("\s+", " ", paragraph_text)
    paragraph_text = re.sub(AutoInsertPandocFootnoteCommand.LABEL_PATTERN, "", paragraph_text)
    paragraph_text = re.sub("\s?\[\Z", "", paragraph_text)
    return(paragraph_text)

  def get_text_in_highlighted_region(self, label_cursor_region):
    highlighted_region = sublime.Region(label_cursor_region.begin() - 1, label_cursor_region.end() - 1)
    highlighted_text = self.view.substr(highlighted_region)
    highlighted_text = self.cleanup_highlighted_text(highlighted_text)
    return(highlighted_text)

  def cleanup_highlighted_text(self, highlighted_text):
    highlighted_text = highlighted_text.strip()
    highlighted_text = re.sub("\n", " ", highlighted_text)
    highlighted_text = re.sub("\s+", " ", highlighted_text)
    highlighted_text = re.sub(AutoInsertPandocFootnoteCommand.LABEL_PATTERN, "", highlighted_text)
    return(highlighted_text)

  def get_start_and_end_position(self, paragraph_text, highlighted_text):
    end_pos   =  len(re.split("\s+", paragraph_text))
    start_pos =  end_pos - len(re.split("\s+", highlighted_text)) + 1 # bc start is loc of 1st word

    if start_pos == 0:
      start_pos = 1

    if start_pos == end_pos:
      pos = "(pos: " + str(start_pos) + ")"
    else:
      pos  = "(pos: " + str(start_pos) + "–" + str(end_pos) + ")"

    return(pos)

######################################################################################
######################################################################################
######################################################################################

#TODO -- use scopes for:
class AutoDeletePandocFootnoteCommand(AutoInsertPandocFootnoteCommand):
  def run(self, edit):
    cursor = self.view.sel()