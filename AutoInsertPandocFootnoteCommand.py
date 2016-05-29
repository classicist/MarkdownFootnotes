#!/usr/bin/python
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
import re

class AutoInsertPandocFootnoteCommand(sublime_plugin.TextCommand):
  LABEL_PATTERN = "\[\^\d+\](?!(\:))"
  ENTRY_PATTERN = "^\[\^\d+\]\:"

  def previous_note_label(self, cursor_region):
    last_note_label = ""
    note_label_region = cursor_region
    note_label_regions = self.view.find_all(self.LABEL_PATTERN)
    if len(note_label_regions) > 0:
      for region in reversed(note_label_regions):
        if region.end() <= cursor_region.begin():
          note_label_region = region
          break
      last_note_label = self.view.substr(note_label_region)
    return(last_note_label)

  def note_label(self, cursor_region):
    note_label_region = self.view.find(self.LABEL_PATTERN, cursor_region.a)
    return(self.view.substr(note_label_region))

  def increment_fn(self, note_label):
    if note_label == "":
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
    entry_text = ""
    if type == "new":
        entry_text = "\n\n%(text)s" % locals()
    if type == "first_or_middle":
        entry_text = "%(text)s\n\n" % locals()
    if type == "last":
        entry_text = "\n%(text)s" % locals()
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
        entry_spot = entry['region'].a
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
      note_pattern  = self.LABEL_PATTERN
      note_template = "[^NN]"
    else:
      note_pattern = self.ENTRY_PATTERN
      note_template = "[^NN]:"
    count = 1

    regions = self.view.find_all(note_pattern)
    for region in regions[0:10]:
      note = note_template.replace("NN", str(count))
      self.view.erase(edit, region)
      self.view.insert(edit, region.a, note)
      count = count + 1

    if len(regions) < 10:
      return

    regions = self.view.find_all(note_pattern)
    for region in regions[10:100]:
      note = note_template.replace("NN", str(count))
      insert_spot = region.a

      if len(note) > region.size():
        print("deco")
        difference =  len(note) - region.size()
        insert_spot = insert_spot + difference

      self.view.erase(edit, region)
      self.view.insert(edit, insert_spot, note)
      count = count + 1

    if len(regions) < 100:
      return
    regions = self.view.find_all(note_pattern)
    for region in regions[100:1000]:
      note = note_template.replace("NN", str(count))
      insert_spot = region.a
      if len(note) > region.size():
        difference =  len(note) - region.size()
        insert_spot = insert_spot + difference
        print("hundo:" + str(difference))

      self.view.erase(edit, region)
      self.view.insert(edit, insert_spot, note)
      count = count + 1


    if len(regions) < 1000:
      return
    regions = self.view.find_all(note_pattern)
    for region in regions[1000:10000]:
      note = note_template.replace("NN", str(count))
      insert_spot = region.a

      if len(note) > region.size():
        difference =  len(note) - region.size()
        insert_spot = insert_spot + difference

      self.view.erase(edit, region)
      self.view.insert(edit, insert_spot, note)
      count = count + 1

# # before: [^9]
# # BOOM -- plus 0
# # after : [^10
# # before: ][^10
# # after : [^11]
# # before:  [^11
# # after : [^12]

# # before: [^9]
# # BOOM -- plus 1
# # after : [^10] -- stomp on the next guy on insert?
# # before: ]^10]
# # after : [^11]


  def move_cursor_to_region(self, region):
    # Clear the cursor's position and move it to `region`.
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
    self.move_cursor_to_region(entry_cursor_region)

#######################################################################################
#######################################################################################
#######################################################################################
# Bugs:
# Given text with notes in it
# and there are 9 notes
# When a "first" ([^1]) note is added to text
# Then the last character after the colon is deleted

#Given there are 10 notes
# When a "first" ([^1]) note is added to text
# Then a new line char is deleted after the colon

#Given [^10] is preceeded by another note without a space (e.g. [^9][^10)
# When a number 1-9 note is added to text, the problem would likey show when wee add note 100 too
#     turning the corner (adding a digit to the note) seems to be the problem, that is,
#     when the note being added is in the lower range (add note 2, causes 10 trouble, add 25, cause 100 problems, etc)
# then the right bracket of the [^10] label is deleted and we see a warning message
# This problem lives in consecutize_numbering("label") for sure
#######################################################################################
#######################################################################################
#######################################################################################

# class AutoInsertPandocFootnoteWithPositionCommand(AutoInsertPandocFootnoteCommand):
#   def get_entry_text(self, type, text, label_cursor_region):
#     text = AutoInsertPandocFootnoteCommand.get_entry_text(self,type, text, label_cursor_region)
#     fn_number = re.findall(r'\d+', text)[0]

#     markdown_line_start      = "\n\n" #Problem: is \A for first line in file, not \n\n
#     paragraph_start_pattern  = "__(\d+|\.|praef|pref)+__"
#     paragraph_middle_pattern = ".*?"
#     paragraph_end_pattern    = "\[\^NN\](?!(\:))"
#     paragraph_pattern = markdown_line_start + paragraph_start_pattern + paragraph_middle_pattern + paragraph_end_pattern
#     paragraph_pattern = re.sub("NN", fn_number, paragraph_pattern)
#     paragraph_region = self.view.find(paragraph_pattern, 0)
#     paragraph_text = self.view.substr(paragraph_region)
#     # paragraph_text = re.sub(AutoInsertPandocFootnoteCommand.LABEL_PATTERN, "", paragraph_text)
#     # paragraph_text = re.sub("^[_|*]+.*?\s", "", paragraph_text) #remove section numbers at begining of paragraph

#     print("label: " + paragraph_pattern + "text: " + paragraph_text)
#     #Goal: translate the beginning and end of the label_cursor_region into word position numbers in paragraph (1 based counting)
#     #get the text from label_cursor_region.end() back to beginning of markdown paragraph (blank new line)
#     #remove the footnotes and all non-alphanumerics
#     #count the spaces to label_cursor_region.begin()
#     #count the spaces to label_cursor_region.end()


#     return(text)

  # def run(self, edit):
  #   AutoInsertPandocFootnoteCommand.run(self, edit)

#Features:
#add (pos:1-11) to fn


