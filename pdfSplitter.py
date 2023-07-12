import re
import math
import pdfplumber
from streamlit.runtime.uploaded_file_manager import UploadedFile
from unidecode import unidecode


class pdfSplitter:

    def __init__(self, uploaded_file: UploadedFile, chunk_size: int = 1000) -> None:
        self._file = uploaded_file
        self._chunk_size = chunk_size
        self.pdf_pages = self.__get_text_in_page__()
        self.clean_pages = self.__get_clean_contents__()
        self.summary_page_nb = self.__get_summary_page_nb__()
        self.summary = self.__get_summary__()
        # self.sections = self.__get_content_by_section__()
        self.meta_data = dict()
        self.meta_data["source"] = uploaded_file.name

    def __get_text_in_page__(self):
        pdf_pages = []
        with pdfplumber.open(self._file) as pdf:
            for page in pdf.pages:
                pdf_pages.append(page.extract_text())
        return pdf_pages

    def __get_clean_contents__(self):
        text_pages = [re.split("\n", page) for page in self.pdf_pages]

        # remove Page number in each page
        page_idx = find_page_number_idx(text_pages)
        for page in text_pages:
            page.pop(page_idx)

        # remove head and footnotes in each page
        start, end = find_page_notes(text_pages)

        clean_pages = []
        for page in text_pages:
            if end == 0:
                clean_pages.append(page[start:])
            else:
                clean_pages.append(page[start:end])

        return clean_pages

    def __get_summary_page_nb__(self):
        nb_page = -1
        pattern = r'sommaire\n|table\sdes\smatieres\n|Index\n'

        # Find the beginning page of the table
        for nb_page, page in enumerate(self.pdf_pages):
            text = unidecode(page)
            if re.search(pattern, text, re.IGNORECASE):
                break
        return nb_page

    def __get_summary__(self):
        if self.summary_page_nb != -1:
            return get_list_summary(self.summary_page_nb, self.clean_pages)
        else:
            return []

    def get_chunk_by_section(self):

        summary = remove_page_number_summary(self.summary)
        total_contents = get_total_contents(self.clean_pages, self.summary_page_nb, summary)
        dic_titre = set_dict_for_section(summary, total_contents)

        chunks_list = []
        titres = list(dic_titre.keys())
        titre_lines = list(dic_titre.values())

        start_line = -1
        for idx_titre, end_line in enumerate(titre_lines[:]):
            content = ''
            if start_line == -1:
                start_line = end_line + 1
            else:
                for idx in range(start_line, end_line):
                    content += ' ' + total_contents[idx]
                chunks = get_chunks_with_limit(content, titres[idx_titre - 1], self._chunk_size)
                chunks_list = chunks_list + chunks
                start_line = end_line + 1
        return chunks_list


def get_chunks_with_limit(content, titre, chunk_size):
    chunk_size = chunk_size - len(titre)
    chunks = []
    len_text = len(content)
    if len_text <= chunk_size:
        chunks.append(content)
    else:
        nb_part = math.ceil(len_text / chunk_size)
        start = 0
        for i in range(nb_part):
            end = (i + 1) * chunk_size
            if end > len_text:
                chunk_part = titre + ' : ' + content[start:]
            else:
                chunk_part = titre + ' : ' + content[start:end]
            chunks.append(chunk_part)
            start = end
    return chunks


def find_page_number_idx(text_pages):
    final_page = text_pages[-1]
    nb_final_page = len(text_pages)

    idx = 0
    for idx, line in enumerate(final_page):
        if line.find(str(nb_final_page)) != -1:
            break
    if abs(idx - 0) < abs(idx - len(final_page)):
        return idx
    else:
        return idx - len(final_page)


def find_page_notes(text_pages):
    # start = 0
    end = 0  # if end is 0 in final, it means non line at the last is the same

    final_page = text_pages[-1]
    second_page = text_pages[-2]

    idx = 0
    for idx, line1 in enumerate(final_page):
        line2 = second_page[idx]
        if line1 != line2:
            break
    start = idx

    final_page = final_page[::-1]
    second_page = second_page[::-1]
    for idx, line1 in enumerate(final_page):
        line2 = second_page[idx]
        if line1 != line2:
            break
    end = end - idx

    return start, end


def find_idx_summary(summary):
    pat = '\d+$'

    first_line = -1
    for idx, line in enumerate(summary):
        if re.search(pat, line):
            first_line = idx
            break

    last_line = len(summary)
    for line in reversed(summary):
        if re.search(pat, line):
            break
        else:
            last_line -= 1

    return first_line, last_line


# Confirm summary's total number of pages
def get_list_summary(first_page, clean_pages):
    summary_list = []
    next_page = first_page

    while next_page != -1 and next_page <= len(clean_pages):
        summary = clean_pages[next_page]
        first_line, last_line = find_idx_summary(summary)
        summary_list = summary_list + summary[0:last_line]
        if first_line != -1 and last_line == len(summary):
            next_page = next_page + 1
        else:
            next_page = -1

    if summary_list:
        summary_list = remove_summary_pattern(summary_list)
    return summary_list


def remove_summary_pattern(summary_list):
    pattern = r'sommaire|table\sdes\smatieres|Index'
    remove_summary = []
    for summary in summary_list:
        summary = unidecode(summary)
        if re.search(pattern, summary, re.IGNORECASE):
            remove_summary.append(summary)
        else:
            break
    for summary in remove_summary:
        summary_list.remove(summary)

    return summary_list


def remove_page_number_summary(summary_list):
    new_summary = []
    prefix = ''
    for summary in summary_list:
        parts = re.split('\s', summary)

        page_nb = not None
        if not re.search(r'\d+$', parts[-1]):
            page_nb = None

        if not prefix:
            titre = parts[0]
            if re.search(r'^\d+', parts[1]):
                titre += ' ' + parts[1]
        else:
            titre = prefix

        if page_nb is None:
            prefix = titre
        else:
            new_summary.append(titre)
            prefix = ''
    return new_summary


def find_first_titre_in_pages(current_page, clean_pages, first_titre):
    first_titre = first_titre.lower()

    find_page = -1
    while find_page == -1 and current_page < len(clean_pages):

        contents = clean_pages[current_page]

        for idx, line in enumerate(contents):
            line = line.lower()
            if first_titre.find(line) != -1 or line.find(first_titre) != -1:
                # if re.search(firstTitre, line, re.IGNORECASE) or re.search(line, firstTitre, re.IGNORECASE):
                find_page = current_page
                break

        current_page += 1

    return find_page


def get_total_contents(clean_pages, first_page, new_summary):
    total_contents = []
    first_titre = new_summary[0]

    current_page = first_page + 1
    find_page = find_first_titre_in_pages(current_page, clean_pages, first_titre)

    for page in clean_pages[find_page:]:
        total_contents += page

    return total_contents


def set_dict_for_section(new_summary, total_contents):
    dic_titre = {}
    idx_titre = 0
    titre = new_summary[idx_titre]

    for idx, content in enumerate(total_contents):
        if re.search('^' + titre, content, re.IGNORECASE):
            dic_titre[content] = idx
            idx_titre += 1
            if idx_titre == len(new_summary):
                break
            titre = new_summary[idx_titre]
    return dic_titre
