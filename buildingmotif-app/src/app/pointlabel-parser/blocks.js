Blockly.defineBlocksWithJsonArray([
  // string - url
  {
    type: 'string-url',
    message0: 'url %2 matches to %1',
    args0: [
      {
        type: 'field_input',
        name: 's',
      },
      {
        type: 'field_input',
        name: 'type_name',
      },
    ],
    colour: 180,
    previousStatement: 'any',
    nextStatement: 'any',
  },
  // string - token
  {
    type: 'string-token',
    message0: '%2 matches to %1',
    args0: [
      {
        type: 'field_input',
        name: 's',  
      },
      {
        type: 'field_dropdown',
        name: 'type_name',
        options: [
          [ "Delimiter", "Delimiter" ],
          [ "Identifier", "Identifier" ]
        ]
      },
    ],
    colour: 60,
    previousStatement: 'any',
    nextStatement: 'any',
  },
  //rest
  {
    type: 'rest',
    message0: 'ends with %1',
    args0: [
      {
        type: 'field_input',
        name: 'type_name',
      },
    ],
    colour: 0,
    previousStatement: 'any',
  },
  // substring_n
  {
    type: 'substring_n',
    message0: '%2 matches to next %1 characters',
    args0: [
      {
        type: 'field_number',
        name: 'length',
      },
      {
        type: 'field_input',
        name: 'type_name',
      },
    ],
    colour: 330,
    previousStatement: 'any',
    nextStatement: 'any',
  },
  // choice
  {
    "type": "choice",
    "message0": "One of these",
    "message1": "%1",
    "args1": [
      {"type": "input_statement", "name": "parsers"}
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": 120
  },
    // sequence - wrapper
    {
      "type": "sequence-wrapper",
      "message0": "my parser",
      "message1": "%1",
      "args1": [
        {"type": "input_statement", "name": "parsers"}
      ],
      "colour": 200
    },
    // sequence-internal
    {
      "type": "sequence-internal",
      "message0": "all of these",
      "message1": "%1",
      "args1": [
        {"type": "input_statement", "name": "parsers"}
      ],
      "colour": 250,
      "previousStatement": null,
      "nextStatement": null,
    },
]);