# RythuCall

## Project Idea

RythuCall is a voice-first fertilizer access prototype designed to help farmers who may not have smartphones or may face difficulty using smartphone-based fertilizer services.

## Problem

Farmers may face difficulty accessing fertilizer through smartphone-based digital services.

Some farmers do not have smartphones or are not comfortable using smartphone applications and may depend on their children or other family members.

Even when a smartphone is available, finding a nearby fertilizer outlet with sufficient and recently updated stock can be difficult.

This can result in repeated checking, long waiting times, and unnecessary travel to distant fertilizer outlets.

## Personal Motivation

This problem was observed while trying to help a family member book fertilizer.

The farmer needed fertilizer, but using the smartphone-based service was difficult. The nearest suitable outlet did not reliably appear, while an outlet much farther away was shown.

For a small quantity of fertilizer, travelling a long distance was not practical.

This motivated the idea of providing a simpler voice-first access method.

## Proposed Solution

RythuCall provides an alternative voice-first access layer.

A farmer can call a toll-free number from a registered mobile number.

The system can identify the farmer profile through an authorized government integration in a real deployment.

The farmer's land information and fertilizer eligibility can then be retrieved automatically.

The system searches available fertilizer outlets and recommends the nearest suitable outlet with sufficient stock.

The farmer can confirm the reservation and receive a booking code by SMS.

The outlet can verify the booking and complete the fertilizer collection.

## Main Journey

1. Farmer calls RythuCall.
2. Farmer selects a language.
3. Farmer is securely authenticated.
4. Farmer profile is identified.
5. Land information is retrieved.
6. Eligible fertilizer quantity is determined.
7. Nearby outlets are searched.
8. Outlets are ranked based on suitability.
9. Farmer confirms the reservation.
10. A booking ID is generated.
11. Farmer receives the booking information.
12. Outlet verifies the booking.
13. Fertilizer is collected.

## Prototype Scope

The prototype will use synthetic farmer, land, fertilizer and outlet data.

It will not connect to real government systems.

It will not use real Aadhaar numbers, OTPs, farmer records, payment information or government inventory.

The toll-free call experience will be simulated in the prototype.

## OpenAI Usage

OpenAI will be used to understand natural-language farmer requests and support multilingual interaction.

For example, a farmer may express a fertilizer request in Telugu.

The AI can convert the request into structured information such as fertilizer type, quantity and user intent.

The backend will make the actual eligibility, inventory and reservation decisions.

## Production Considerations

A production version would require authorized integration with relevant government identity, land, fertilizer inventory and outlet systems.

It would require secure authentication, encryption, authorization, audit logging, data minimization and appropriate government approvals.

The prototype does not claim to be an official government service.

## Status

Prototype development started in August 2026.