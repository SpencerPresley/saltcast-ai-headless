import re

class MarkdownBuffer:
    """
    A class to process Markdown text into HTML, handling nested lists and inline formatting.
    
    This class processes Markdown text chunk by chunk, maintaining state to properly
    handle nested structures like lists.
    """

    def __init__(self):
        self.buffer = ""
        self.current_line = ""
        self.list_stack = []  # Stores (list_type, indent, last_number) for each list level
        self.in_list_item = False

    def add_chunk(self, chunk):
        """
        Add a new chunk of text to the buffer and process it.
        
        Args:
            chunk (str): The new text to process.
        
        Returns:
            list: Processed HTML elements.
        """
        self.buffer += chunk
        return self._process_buffer()

    def _process_buffer(self):
        """
        Process the current buffer, splitting it into lines and handling each line.
        
        Returns:
            list: Processed HTML elements.
        """
        processed_chunks = []
        new_lines = self.buffer.split('\n')
        
        # Process all complete lines
        for line in new_lines[:-1]:
            self.current_line += line
            processed_chunks.extend(self._process_line(self.current_line))
            self.current_line = ""
        
        # Keep the last (potentially incomplete) line in the buffer
        self.current_line += new_lines[-1]
        self.buffer = ""
        
        # Process the current line if it's getting long
        if len(self.current_line) > 80:
            processed_chunks.extend(self._process_line(self.current_line))
            self.current_line = ""
        
        return processed_chunks

    def _process_line(self, line):
        """
        Process a single line of text, determining its type and formatting accordingly.
        
        Args:
            line (str): The line to process.
        
        Returns:
            list: Processed HTML elements for this line.
        """
        stripped_line = line.lstrip()
        indent = len(line) - len(stripped_line)
        
        if re.match(r'^#{1,6}\s', stripped_line):
            return self._process_header(stripped_line)
        elif re.match(r'^\d+\.\s', stripped_line):
            return self._process_ordered_list_item(stripped_line, indent)
        elif stripped_line.startswith('- '):
            return self._process_unordered_list_item(stripped_line, indent)
        elif stripped_line.strip() == '':
            return self._process_empty_line()
        else:
            return self._process_text(stripped_line, indent)

    def _process_header(self, line):
        """Process a header line."""
        self._close_lists()
        match = re.match(r'^(#{1,6})\s(.+)$', line)
        level = len(match.group(1))
        content = self._format_inline(match.group(2))
        return [f"<h{level}>{content}</h{level}>"]

    def _process_ordered_list_item(self, line, indent):
        """Process an ordered list item."""
        match = re.match(r'^(\d+)\.\s(.+)$', line)
        number = int(match.group(1))
        content = self._format_inline(match.group(2))
        return self._handle_list_item('ol', number, content, indent)

    def _process_unordered_list_item(self, line, indent):
        """Process an unordered list item."""
        content = self._format_inline(line[2:])
        return self._handle_list_item('ul', None, content, indent)

    def _process_empty_line(self):
        """Process an empty line."""
        if self.in_list_item:
            self.in_list_item = False
        return ["<br>"]

    def _process_text(self, line, indent):
        """Process a line of regular text."""
        if self.in_list_item:
            self.in_list_item = False
            return [f" {self._format_inline(line)}"]
        else:
            self._close_lists_if_needed(indent)
            return [self._format_inline(line)]

    def _handle_list_item(self, list_type, number, content, indent):
        """
        Handle a list item, managing nested lists and list numbering.
        
        Args:
            list_type (str): Either 'ol' or 'ul'.
            number (int or None): The number for ordered list items, None for unordered.
            content (str): The content of the list item.
            indent (int): The indentation level of the list item.
        
        Returns:
            list: HTML elements for this list item.
        """
        result = []
        
        # Close lists that are no longer relevant
        while self.list_stack and self.list_stack[-1][1] > indent:
            result.extend(self._close_list())
        
        # Start a new list if necessary
        if not self.list_stack or self.list_stack[-1][1] < indent or self.list_stack[-1][0] != list_type:
            if list_type == 'ol':
                result.append(f"<ol start='{number}'>")
            else:
                result.append(f"<{list_type}>")
            self.list_stack.append([list_type, indent, number if list_type == 'ol' else None])
        
        if list_type == 'ol':
            last_number = self.list_stack[-1][2]
            if number != last_number + 1:
                result.append(f"<li value='{number}'>")
            else:
                result.append("<li>")
            self.list_stack[-1][2] = number
        else:
            result.append("<li>")
        
        result.append(content)
        self.in_list_item = True
        return result

    def _close_lists_if_needed(self, indent):
        """Close any open lists if we've moved to a less indented level."""
        result = []
        while self.list_stack and self.list_stack[-1][1] > indent:
            result.extend(self._close_list())
        return result

    def _close_list(self):
        """Close the most recently opened list."""
        if self.list_stack:
            list_type, _, _ = self.list_stack.pop()
            return ["</li>", f"</{list_type}>"]
        return []

    def _close_lists(self):
        """Close all open lists."""
        result = []
        while self.list_stack:
            result.extend(self._close_list())
        return result

    def _format_inline(self, text):
        """Apply inline formatting (bold, italic) to text."""
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        return text

    def flush(self):
        """
        Process any remaining content in the buffer and close all open tags.
        
        Returns:
            list: Final processed HTML elements.
        """
        chunks = self._process_line(self.current_line) if self.current_line else []
        chunks.extend(self._close_lists())
        self.current_line = ""
        return chunks
        

# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.current_line = ""
#         self.list_stack = []

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         return self._process_buffer()

#     def _process_buffer(self):
#         processed_chunks = []
#         new_lines = self.buffer.split('\n')
        
#         if len(new_lines) > 1:
#             self.current_line += new_lines[0]
#             processed_chunks.extend(self._process_line(self.current_line))
            
#             for line in new_lines[1:-1]:
#                 processed_chunks.extend(self._process_line(line))
            
#             self.current_line = new_lines[-1]
#             self.buffer = self.current_line
#         else:
#             self.current_line += self.buffer
#             if len(self.current_line) > 80:  # Process if line is getting long
#                 processed_chunks.extend(self._process_line(self.current_line))
#                 self.current_line = ""
#             self.buffer = ""
        
#         return processed_chunks

#     def _process_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = self._format_inline(match.group(2))
#             return [f"<h{level}>{content}</h{level}>"]
#         elif re.match(r'^\d+\.\s', line):
#             match = re.match(r'^(\d+)\.\s(.+)$', line)
#             number = match.group(1)
#             content = self._format_inline(match.group(2))
#             return [f"<ol start='{number}'><li>{content}</li></ol>"]
#         elif line.startswith('- '):
#             content = self._format_inline(line[2:])
#             if not self.list_stack or self.list_stack[-1] != 'ul':
#                 self.list_stack.append('ul')
#                 return [f"<ul><li>{content}</li>"]
#             return [f"<li>{content}</li>"]
#         elif line.strip() == '':
#             if self.list_stack:
#                 tag = self.list_stack.pop()
#                 return [f"</{tag}>"]
#             return ["<br>"]
#         else:
#             return self._stream_process(line)

#     def _stream_process(self, text):
#         chunks = []
#         current_chunk = ""
#         for char in text:
#             current_chunk += char
#             if len(current_chunk) >= 5 or char in ['.', '!', '?', ',', ' ']:
#                 chunks.append(self._format_inline(current_chunk))
#                 current_chunk = ""
#         if current_chunk:
#             chunks.append(self._format_inline(current_chunk))
#         return chunks

#     def _format_inline(self, text):
#         text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
#         text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
#         return text

#     def flush(self):
#         chunks = self._process_line(self.current_line) if self.current_line else []
#         while self.list_stack:
#             tag = self.list_stack.pop()
#             chunks.append(f"</{tag}>")
#         return chunks
    
# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.current_line = ""

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         return self._process_buffer()

#     def _process_buffer(self):
#         processed_chunks = []
#         new_lines = self.buffer.split('\n')
        
#         if len(new_lines) > 1:
#             self.current_line += new_lines[0]
#             processed_chunks.extend(self._process_line(self.current_line))
            
#             for line in new_lines[1:-1]:
#                 processed_chunks.extend(self._process_line(line))
            
#             self.current_line = new_lines[-1]
#             self.buffer = self.current_line
#         else:
#             self.current_line += self.buffer
#             if len(self.current_line) > 80:  # Process if line is getting long
#                 processed_chunks.extend(self._process_line(self.current_line))
#                 self.current_line = ""
#             self.buffer = ""
        
#         return processed_chunks

#     def _process_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = match.group(2)
#             return [f"<h{level}>{content}</h{level}>"]
#         elif line.startswith('- '):
#             content = line[2:]
#             return [f"<li>{self._format_inline(content)}</li>"]
#         else:
#             return self._stream_process(line)

#     def _stream_process(self, text):
#         chunks = []
#         current_chunk = ""
#         for char in text:
#             current_chunk += char
#             if len(current_chunk) >= 5 or char in ['.', '!', '?', ',', ' ']:
#                 chunks.append(self._format_inline(current_chunk))
#                 current_chunk = ""
#         if current_chunk:
#             chunks.append(self._format_inline(current_chunk))
#         return chunks

#     def _format_inline(self, text):
#         text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
#         text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
#         return text

#     def flush(self):
#         return self._process_line(self.current_line) if self.current_line else []

# WORKS
# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.complete_elements = []

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         return self._process_buffer()

#     def _process_buffer(self):
#         lines = self.buffer.split('\n')
#         self.buffer = lines.pop() if lines else ""  # Keep the last incomplete line in the buffer
        
#         processed_chunks = []
        
#         for line in lines:
#             if line.strip():
#                 if re.match(r'^#{1,6}\s', line) or line.startswith('- '):
#                     processed_chunks.append(self._format_line(line))
#                 else:
#                     processed_chunks.extend(self._stream_process(line))
#             else:
#                 processed_chunks.append("<br>")
        
#         return processed_chunks

#     def _format_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = match.group(2)
#             return f"<h{level}>{content}</h{level}>"
#         elif line.startswith('- '):
#             content = line[2:]
#             content = self._format_inline(content)
#             return f"<li>{content}</li>"
#         else:
#             return self._format_inline(line)

#     def _stream_process(self, text):
#         chunks = []
#         current_chunk = ""
#         for char in text:
#             current_chunk += char
#             if len(current_chunk) >= 5 or char in ['.', '!', '?', ',']:
#                 chunks.append(self._format_inline(current_chunk))
#                 current_chunk = ""
#         if current_chunk:
#             chunks.append(self._format_inline(current_chunk))
#         return chunks

#     def _format_inline(self, text):
#         text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
#         text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
#         return text

#     def flush(self):
#         chunks = self._process_buffer()
#         if self.buffer:
#             chunks.extend(self._stream_process(self.buffer))
#             self.buffer = ""
#         return chunks

# BEST ONE SO FAR
# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.complete_elements = []
#         self.current_paragraph = ""

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         self._process_buffer()

#     def _process_buffer(self):
#         lines = self.buffer.split('\n')
#         self.buffer = lines.pop() if lines else ""  # Keep the last incomplete line in the buffer

#         for line in lines:
#             if line.strip():
#                 element = self._format_line(line)
#                 if element.startswith('<p>'):
#                     self.current_paragraph += element[3:-4] + " "
#                 else:
#                     if self.current_paragraph:
#                         self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                         self.current_paragraph = ""
#                     self.complete_elements.append(element)
#             elif self.current_paragraph:
#                 self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                 self.current_paragraph = ""
#             else:
#                 self.complete_elements.append("<br>")

#     def _format_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = match.group(2)
#             return f"<h{level}>{content}</h{level}>"
#         elif line.startswith('- '):
#             content = line[2:]
#             content = self._format_inline(content)
#             return f"<li>{content}</li>"
#         else:
#             return f"<p>{self._format_inline(line)}</p>"

#     def _format_inline(self, text):
#         text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
#         text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
#         return text

#     def get_complete_elements(self):
#         elements = self.complete_elements
#         self.complete_elements = []
#         return elements

#     def flush(self):
#         if self.buffer:
#             self._process_buffer()
#         if self.current_paragraph:
#             self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#             self.current_paragraph = ""
#         return self.get_complete_elements()

# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.complete_elements = []
#         self.current_paragraph = ""

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         self._process_buffer()

#     def _process_buffer(self):
#         lines = self.buffer.split('\n')
#         self.buffer = lines.pop() if lines else ""  # Keep the last incomplete line in the buffer

#         for line in lines:
#             if line.strip():
#                 element = self._format_line(line)
#                 if element.startswith('<p>'):
#                     self.current_paragraph += element[3:-4] + " "
#                 else:
#                     if self.current_paragraph:
#                         self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                         self.current_paragraph = ""
#                     self.complete_elements.append(element)
#             elif self.current_paragraph:
#                 self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                 self.current_paragraph = ""
#             else:
#                 self.complete_elements.append("<br>")

#     def _format_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = match.group(2)
#             return f"<h{level}>{content}</h{level}>"
#         elif line.startswith('- '):
#             content = line[2:]
#             return f"<li>{content}</li>"
#         else:
#             line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
#             line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
#             return f"<p>{line}</p>"

#     def get_complete_elements(self):
#         elements = self.complete_elements
#         self.complete_elements = []
#         return elements

#     def flush(self):
#         if self.buffer:
#             self._process_buffer()
#         if self.current_paragraph:
#             self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#             self.current_paragraph = ""
#         return self.get_complete_elements()

# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.complete_elements = []
#         self.current_paragraph = ""

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         self._process_buffer()

#     def _process_buffer(self):
#         lines = self.buffer.split('\n')
#         self.buffer = lines.pop()  # Keep the last incomplete line in the buffer

#         for line in lines:
#             if line.strip():
#                 element = self._format_line(line)
#                 if element.startswith('<p>'):
#                     self.current_paragraph += element[3:-4] + " "
#                 else:
#                     if self.current_paragraph:
#                         self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                         self.current_paragraph = ""
#                     self.complete_elements.append(element)
#             elif self.current_paragraph:
#                 self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#                 self.current_paragraph = ""

#     def _format_line(self, line):
#         if re.match(r'^#{1,6}\s', line):
#             match = re.match(r'^(#{1,6})\s(.+)$', line)
#             level = len(match.group(1))
#             content = match.group(2)
#             return f"<h{level}>{content}</h{level}>"
#         elif line.startswith('- '):
#             content = line[2:]
#             return f"<li>{content}</li>"
#         else:
#             line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
#             line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
#             return f"<p>{line}</p>"

#     def get_complete_elements(self):
#         elements = self.complete_elements
#         self.complete_elements = []
#         return elements

#     def flush(self):
#         if self.buffer:
#             self._process_buffer()
#         if self.current_paragraph:
#             self.complete_elements.append(f"<p>{self.current_paragraph.strip()}</p>")
#             self.current_paragraph = ""
#         return self.get_complete_elements()
        
# class MarkdownBuffer:
#     def __init__(self):
#         self.buffer = ""
#         self.complete_elements = []
#         self.current_element = None

#     def add_chunk(self, chunk):
#         self.buffer += chunk
#         self._process_buffer()

#     def _process_buffer(self):
#         while True:
#             if self.current_element:
#                 end_tag = f"</{self.current_element['tag']}>"
#                 end_index = self.buffer.find(end_tag)
#                 if end_index != -1:
#                     self.current_element['content'] += self.buffer[:end_index]
#                     self.complete_elements.append(f"<{self.current_element['tag']}>{self.current_element['content']}</{self.current_element['tag']}>")
#                     self.buffer = self.buffer[end_index + len(end_tag):]
#                     self.current_element = None
#                 else:
#                     self.current_element['content'] += self.buffer
#                     self.buffer = ""
#                     break
#             else:
#                 match = re.match(r'^(#{1,6})\s(.+?)$|^```(\w*)$|^[-*+]\s(.+?)$|\*\*(.*?)\*\*|\*(.*?)\*|<br>', self.buffer, re.MULTILINE)
#                 if match:
#                     if match.group(1):  # Header
#                         level = len(match.group(1))
#                         content = match.group(2)
#                         self.complete_elements.append(f"<h{level}>{content}</h{level}>")
#                         self.buffer = self.buffer[match.end():]
#                     elif match.group(3) is not None:  # Code block start
#                         lang = match.group(3)
#                         self.current_element = {'tag': 'pre', 'content': f'<code class="language-{lang}">'}
#                         self.buffer = self.buffer[match.end():]
#                     elif match.group(4):  # Bullet point
#                         content = match.group(4)
#                         self.complete_elements.append(f"<li>{content}</li>")
#                         self.buffer = self.buffer[match.end():]
#                     elif match.group(5):  # Bold
#                         content = match.group(5)
#                         self.complete_elements.append(f"<strong>{content}</strong>")
#                         self.buffer = self.buffer[match.end():]
#                     elif match.group(6):  # Italic
#                         content = match.group(6)
#                         self.complete_elements.append(f"<em>{content}</em>")
#                         self.buffer = self.buffer[match.end():]
#                     elif match.group(0) == '<br>':  # Line break
#                         self.complete_elements.append("<br>")
#                         self.buffer = self.buffer[match.end():]
#                 else:
#                     break

#     def get_complete_elements(self):
#         elements = self.complete_elements
#         self.complete_elements = []
#         return elements
