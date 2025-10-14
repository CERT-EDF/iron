# EDF Iron Server


## Introduction

This server implements the API for Iron service. It uses EDF Fusion framework as a library to ease maintainance and take advantage of new generic features as they become available.

> [!TIP]
> This documentation does not aim at completeness but provides an overview of the main features


## Services

Iron offers a single web interface to perform case management operations across different services including:

- [Carbon](https://github.com/cert-edf/carbon)
- [Helium](https://github.com/cert-edf/helium)
- [Neon](https://github.com/cert-edf/neon)
- [DFIR-IRIS](https://github.com/dfir-iris/iris-web)

New service integration requires the service to implement `FusionCaseAPI` defined in the [fusion library](https://github.com/cert-edf/fusion). If the service does not directly implement the API, an API proxy or middleware can be implemented. Carbon, Helium and Neon implement the API directly. DFIR-IRIS is integrated through a middleware.


## Events

Iron, when configured to do so, can emit events using webhooks. Here is a list of event's categories it can emit:

- `create_case`
- `update_case`

Event's structure looks like this:

```json
{
    "source": "event's source, service's name is often used as source",
    "category": "event's category, the nature of the event",
    "case": {},
    "ext": {},
}
```

Both `case` and `ext` are objects used to store information respectively about the case related to the event and extended data specific to the event.

Iron's configuration allows to define a general webhook which receives all events for all cases. It is also possible to define per-case webhooks to trigger case specific scenarios.
