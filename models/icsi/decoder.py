import sys, os
from .ilp import IntegerLinearProgram

def decode_simple(max_length, sentence_length_file, concepts_in_sentence_file, concept_weight_file, timelimit=100, command="glpsol"):
    solver = IntegerLinearProgram(debug=0, tmp = "tmp_decoder.%d.%s.%s" % (os.getpid(), os.environ.get("USER", "guest"), os.environ.get("HOSTNAME", "localhost")), command=command, time_limit=timelimit)

    alpha = 1
    concept_id, concept, concept_weights = getConcepts(concept_weight_file, alpha, 'concept')

    index = {};	 sentence_concepts = {}
    index, sentence_concepts = getSentencesWithConcepts(concepts_in_sentence_file, concept_id)
                    
    # build objective
    objective = []
    for concept, weight in concept_weights.items():
        if concept not in index: continue # skip unused concepts
        objective.append("%+g c%d" % (alpha*weight, concept))
        solver.binary["c%d" % concept] = concept
    solver.objective["score"] = " ".join(objective)

    # binary sentences
    for sentence, concepts in sentence_concepts.items():
        solver.binary["s%d" % sentence] = sentence

    # concept => sentence (absent from original)
    #DON 'T NEED THIS, SINCE THE SYSTEM WILL TRY TO INCLUDE AS MANY CONCEPTS AS POSSIBLE ANYWAYS

    # sentences => concepts
    for concept in index:
        solver.constraints["index_%d" % len(solver.constraints)] = " + ".join(["s%d" % x for x in index[concept]]) + " - c%d >= 0" % concept

    length_constraint = []
    sentence = 0
    for line in open(sentence_length_file):
        if sentence in sentence_concepts :
            length = line.strip()
            length_constraint.append("%s s%d" % (length, sentence))
#			solver.objective["score"] += " - %g s%d" % (float(length) / 1000.0, sentence)
        sentence += 1

    solver.constraints["length_%d" % len(solver.constraints)] = " + ".join(length_constraint) + " <= " + str(max_length)

    # sys.stderr.write("ilp: %d sentences, %d concepts\n" % (len(sentence_concepts), len(index)))

    if len(sentence_concepts) > 0 and len(index) > 0:
        # print("SOLVING")
        solver.run()
        # print("SOLVED")
    output = []
    for variable in solver.output:
        if variable.startswith("s") and solver.output[variable] == 1:
            output.append(int(variable[1:]))
    return output
    
def getConcepts(concept_weight_file, contribution, conceptname):
    concept_id={}
    concept=0
    concept_weights={}
    if contribution>0:
        for line in open(concept_weight_file):
            tokens = line.strip().split()
            weight = float(tokens[1])
            if tokens[0] in concept_id:
                sys.stderr.write('ERROR: duplicate '+conceptname+' \"%s\", line %d in %s\n' % (tokens[0], neconcept + 1, concept_weight_file))
                sys.exit(1)
            concept_id[tokens[0]] = concept
            concept_weights[concept] = weight
            concept += 1
    return concept_id, concept, concept_weights


def getSentencesWithConcepts(concepts_in_sentence_file, concept_id):
    index = {};	 sentence_concepts = {};	sentence = 0
    for line in open(concepts_in_sentence_file):
        tokens = line.strip().split()
        concepts = {}
        for token in tokens:
            concepts[token] =True
        mapped_concepts = {}
        # print(concept_id)
        for concept in concepts:
            id = concept_id[concept]
            if id not in index: index[id] = []
            index[id].append(sentence) #concept:[sentences]
            mapped_concepts[id] =True
        if len(mapped_concepts) > 0:
            sentence_concepts[sentence] = mapped_concepts #sentence:[concept:freq pairs]
        sentence += 1
    return index, sentence_concepts