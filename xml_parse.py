import xmltodict
import json
import parse_tree


def opinion_parse(sentence):
    # from ~ toの値を求める(単語抽出)
    aspect_word = []
    flag = False
    for opinion in sentence["Opinions"]["Opinion"]:
        if type(opinion) is not dict:
            opinion = sentence["Opinions"]["Opinion"]
            flag = True
        if int(opinion["@to"]) == 0:
            continue
        aspect_word.append(sentence["text"][int(opinion["@from"]): int(opinion["@to"])])
        if flag:
            break
    if aspect_word == [''] or not aspect_word:
        return None
    aspect_word.append("|||")
    return aspect_word


def word_parse(sentence, aspect_word):
    spell = ''
    split_sentence = []
    words_num = 0
    aspect_from_to_index = [[words_num] * 3 for _ in range(len(aspect_word))]

    for word in sentence["text"]:
        if word == ' ':
            if spell != '':
                words_num += 1
                split_sentence.append(spell)
                spell = ''
        elif word == '.' or word == ',' or word == '!':
            if spell != '':
                split_sentence.append(spell)
                split_sentence.append(word)
            spell = ''
        else:
            spell += word

        # from ~ toの値を求める
        for i, as_word in enumerate(aspect_word):
            if as_word[aspect_from_to_index[i][2]] == word:
                aspect_from_to_index[i][2] += 1
                if len(as_word) == aspect_from_to_index[i][2]:
                    aspect_from_to_index[i][2] = 0
                    aspect_from_to_index[i][1] = words_num + 1
            else:
                aspect_from_to_index[i][2] = 0
                if aspect_from_to_index[i][1] == 0:
                    aspect_from_to_index[i][0] = words_num
    if spell != '':
        split_sentence.append(spell)
    split_sentence.append('-')

    return aspect_from_to_index, split_sentence


def sentence_parse(sentence):
    if 'Opinions' not in sentence:
        return None, None, None

    if not sentence["Opinions"]:
        return None, None, None

    aspect_word = opinion_parse(sentence)
    if not aspect_word:
        return None, None, None

    # 単語をいい感じに分割 token...
    aspect_from_to_index, split_sentence = word_parse(sentence, aspect_word)

    # debug
    # print(aspect_from_to_index, aspect_word, sentence["text"])

    # アスペクトの部分 aspects + aa_choice
    aspect = None
    aspect_detail = None
    index = 0
    flag = False
    for opinion in sentence["Opinions"]["Opinion"]:
        if type(opinion) is not dict:
            opinion = sentence["Opinions"]["Opinion"]
            flag = True
        if int(opinion["@to"]) == 0:
            continue
        aspect_detail = {
            'select_idx': list(map(lambda x: x - 1, aspect_from_to_index[index][:2])),
            'word_range': [int(opinion['@from']), int(opinion['@to'])],
            'polarity_pair': [""] * 2,
        }
        aspect = {
            'term': [opinion['@category']], 'from': aspect_from_to_index[index][0],
            'to': aspect_from_to_index[index][1], 'polarity': opinion['@polarity'],
        }
        index += 1
        if flag:
            break
    return split_sentence, aspect, aspect_detail


def xml_to_json_for_english(file_name):
    with open(file_name, encoding='utf-8') as fp:
        # xml読み込み
        xml_data = fp.read()

        # xml → dict
        dict_data = xmltodict.parse(xml_data)
        json_data = []
        for token in dict_data["Reviews"]["Review"]:
            data = {}
            # dataにいれるやつ
            token_word = []
            aspects = []
            aa_choice = []
            flag = False
            for sentence in token["sentences"]["sentence"]:
                if type(sentence) is not dict:
                    flag = True
                    split_sentence, aspect, aspect_detail = sentence_parse(token["sentences"]["sentence"])
                else:
                    split_sentence, aspect, aspect_detail = sentence_parse(sentence)
                if split_sentence and aspect and aspect_detail:
                    token_word += split_sentence
                    aspects.append(aspect)
                    aa_choice.append(aspect_detail)
                if flag:
                    break
            if not token_word:
                continue
            token_word.pop(-1)
            data['token'] = token_word
            data['aspects'] = aspects
            data['aa_choice'] = aa_choice
            json_data.append(data)
    return json_data


def clear_json_data(file_name):
    with open(file_name, 'r') as f:
        json_data = json.load(f)
    with open(file_name, 'w') as f:
        json.dump(json_data, f, indent=4)


def xml_parse(json_file_name, xml_file_name):
    with open(json_file_name, 'w') as f:
        json_data = xml_to_json_for_english(xml_file_name)
        json.dump(json_data, f, indent=4)
    parse_tree.preprocess_file(json_file_name)
    clear_json_data(json_file_name)


def main():
    json_file_name = 'data/en/restaurant/test_con.json'
    xml_file_name = 'data/xml/EN_REST_SB1_TEST.xml'
    xml_parse(json_file_name, xml_file_name)
    clear_json_data(json_file_name)


if __name__ == '__main__':
    main()
