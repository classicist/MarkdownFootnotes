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
    self.view.insert(edit, label_cursor_region.a, new_note_lable)
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

  def insert_new_entry(self, edit, label_cursor_region):
    label_before_previous_label = self.previous_note_label(label_cursor_region)
    previous_label = self.increment_fn(label_before_previous_label)
    entry = self.entry_for_label(previous_label)
    raw_entry = entry['entry']
    is_first_or_middle_position_entry = (raw_entry != "")
    entries_exist = len(self.view.find_all(self.ENTRY_PATTERN)) > 0

    if entries_exist:
      if is_first_or_middle_position_entry:
        entry_text = "%(raw_entry)s\n\n" % locals()
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
        entry_text = "\n\n%(entry_text)s" % locals()
        self.view.insert(edit, entry_spot, entry_text)
        new_region = self.view.find_all(self.ENTRY_PATTERN)[-1]
        entry_cursor_region = new_region
    else: #no entries exist in the file yet, this is the first
      entry_text = "\n\n[^1]:"
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
    regions = self.view.find_all(note_pattern)
    count = 1

    for region in regions:
      note = note_template.replace("NN", str(count))

      if len(note) > region.size():
        difference =  len(note) - region.size()
        region.b = region.b + difference

      self.view.replace(edit, region, note)
      count = count + 1

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
      sublime.error_message("Some footnotes do have a body: There are %(no_of_labels)s footnotes in the text and %(no_of_entries)s footnotes in the footer." % locals())
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

# TODO: Edge cases for adding entries
# TODO: [^1]:(pos:1-11) hominum — cain om. S
