import sublime, sublime_plugin, re

class AutoInsertPandocFootnoteCommand(sublime_plugin.TextCommand):
  def previous_note_label(self, cursor_region):
    note_label_pattern = "\[\^\d+\](?!(\:))"
    last_note_label = ""
    note_label_region = cursor_region
    note_label_regions = self.view.find_all(note_label_pattern)
    if len(note_label_regions) > 0:
      for region in reversed(note_label_regions):
        if region.b <= cursor_region.a:
          note_label_region = region
          break
      last_note_label = self.view.substr(note_label_region)
    return(last_note_label)

  def note_label(self, cursor_region):
    note_label_pattern = "\[\^\d+\](?!(\:))"
    note_label_region = self.view.find(note_label_pattern, cursor_region.a)
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

  def insert_new_entry(self, edit, label_cursor_region):
    penulitmate_note_label = self.previous_note_label(label_cursor_region)
    last_note_label = self.increment_fn(penulitmate_note_label)
    entry = self.entry_for_label(last_note_label)
    raw_entry = entry['entry']
    if raw_entry != "": #all good
      entry_text = "%(raw_entry)s\n\n" % locals()
      entry_spot = entry['region'].a
      entry_cursor_region = entry['region']
    else:
      entry_regions = self.view.find_all("^\[\^\d+?\]\:.*?\n")
      if len(entry_regions) > 0: #there are entries, but none for our label
        last_region = entry_regions[-1]
        entry_spot = last_region.b
        entry_cursor_region = last_region
        last_entry = self.view.substr(last_region)
        inc = int(re.findall(r'\d+', last_entry)[0]) + 1
        entry_text = re.sub('\d+', str(inc), last_entry)
        entry_text = "\n%(entry_text)s" % locals()
    self.view.insert(edit, entry_spot, entry_text)
    return(entry_cursor_region)

  def consecutize_numbering(self, edit, note_type = "label"):
    if note_type == "label":
      note_pattern  = "\[\^\d+\](?!(\:))"
      note_template = "[^NN]"
    else:
      note_pattern = "^\[\^\d+\]\:"
      note_template = "[^NN]:"

    regions = self.view.find_all(note_pattern)
    count = 1
    for region in regions:
      note = note_template.replace("NN", str(count))
      self.view.replace(edit, region, note)
      count = count + 1

  def move_cursor_to_new_entry(self, entry_cursor_region):
    # Clear the cursor's position and move it to `region`.
    entry_cursor_region.a = entry_cursor_region.b
    cursor = self.view.sel()
    self.original_position = cursor[0]
    cursor.clear()
    cursor.add(entry_cursor_region)
    self.view.show(entry_cursor_region)

  def run(self, edit):
    label_cursor_region = self.insert_new_note(edit)
    entry_cursor_region = self.insert_new_entry(edit, label_cursor_region)
    self.consecutize_numbering(edit, "label")
    self.consecutize_numbering(edit, "entry")
    self.move_cursor_to_new_entry(entry_cursor_region)

# TODO: [^1]:(pos:1-11) hominum — cain om. S
# TODO: Edge cases for adding entries
