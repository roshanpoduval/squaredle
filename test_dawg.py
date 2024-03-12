# docker build . -t dawg_image -f dawg.dockerfile; docker run --name dawg_container -v $(pwd):$(pwd) -w $(pwd) -it dawg_image ; nohup docker container rm dawg_container
import json
import dawg
file_nm = 'NSWL2020'
with open(f'{file_nm}.json') as f:
    words_dict = json.load(f)
d = dawg.DAWG(words_dict.keys())
d.save(f'{file_nm}.dawg')
d = dawg.CompletionDAWG(words_dict.keys())
d.save(f'{file_nm}.completion.dawg')