# README #

## REST API Endpoints ##

**Base URL:** [http://mms-api-1043.appspot.com](http://mms-api-1043.appspot.com)

1. /info/<expansion name\>/<card name\> - info of a single product
    - Sample: [/info/khans%20of%20tarkir/mantis%20rider](http://mms-api-1043.appspot.com/info/khans%20of%20tarkir/mantis%20rider)    

1. /info/<expansion name\> - info of all products of a single expansion (accepts simple filters)
    - Sample: [/info/khans%20of%20tarkir](http://mms-api-1043.appspot.com/info/khans%20of%20tarkir)
    - with filter: [/info/khans%20of%20tarkir?rarity=mythic](http://mms-api-1043.appspot.com/info/khans%20of%20tarkir?rarity=mythic)
    