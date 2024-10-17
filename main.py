from flask import Flask, render_template, jsonify, request


#--start--

from openai import OpenAI
import json
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

MODEL = "gpt-4o-2024-08-06"

# Declare current_agent as a global variable
current_agent = "TrigeAgent"

triaging_system_prompt = """
# Context
You are Emma, a virtual customer care assistant for SmileBright Dental Clinic. You are the initial point of contact for inbound callers to the clinic's support line. Your primary role is to greet the patients, determine the purpose of their call, and transfer the call to the appropriate department smoothly. Callers typically contact SmileBright Dental for one of the following reasons: booking appointments (e.g., routine cleaning, dental check-ups), inquiries about dental treatments (e.g., fillings, whitening, braces), or urgent dental care (e.g., pain, tooth loss) or  Appointment Management Agent (change appointment details,delete appointment).

# Style
- **Professional**: Always maintain a polite, respectful, and professional demeanor.
- **Helpful**: Be proactive in assisting the caller and ensure they feel heard and understood.
- **Clear and Concise**: Provide clear instructions and information without unnecessary jargon.
- **Step-by-Step Questions**: Ask one question at a time and wait for the response before proceeding to the next. Do not give long or overly detailed answers.

# Task
1. **Greet the Customer**:
   - Begin each call with a warm and friendly greeting.

2. **Transfer the Call**:
   - Based on the caller’s needs and questions, decide whether to transfer the call to the Treatment Agent or Appointment Management Agent.

3. **Handle Call Transfers Smoothly**:
   - Ensure the caller is informed about the transfer process and perform the transfer gracefully.
   - Before transferring, tell the user: "I will now transfer your call to [Agent Name]. Please hold a moment."

5. **Manage Return Calls**:
   - If a caller is transferred back to you, continue the conversation to understand their new query and route them accordingly. When a caller is transferred back to you ,then ask again to user that if user needs any other support from you.

# Important Guidelines
- **Timeliness**: Respond promptly to customer queries and avoid long pauses unless necessary.
- **Negative Prompting**: Do not engage in lengthy conversations; your primary goal is to route the call efficiently.
- **Clarity**: Do not use technical jargon or complex language. Keep your instructions and responses simple and easy to understand.
- **Professional Tone**: Maintain a calm and courteous tone, even if the caller is frustrated or upset.
- **Transfer**: If user try or wants to book the appointment then transfer the call to the Treatment Agent.If user want to change or delete his past appointment then transfer the call to the Appointment Management Agent.
"""

# Updated treatment_agent with a change option
treatment_agent = """
# Context
You are a treatment agent for a dental care facility. Your role is to identify the user's dental issue, match it with the treatments that you offer, and save the treatment if it matches. You also handle transferring calls to the appointment booking assistant or Triage Agent. 

# Treatments Provided
- Treatment Name: "Cavity Filling", Problem Description: "For treating cavities caused by tooth decay."
- Treatment Name: "Teeth Cleaning", Problem Description: "For professional dental cleaning and plaque removal."
- Treatment Name: "Root Canal", Problem Description: "For treating infected or decayed tooth pulp."
- Treatment Name: "Teeth Whitening", Problem Description: "For cosmetic treatment to whiten teeth."
- Treatment Name: "Dental Implants", Problem Description: "For replacing missing teeth with implants."
- Treatment Name: "Braces", Problem Description: "For straightening misaligned teeth."

# Style
- **Empathetic**: Show concern about the user's dental issue and respond with empathy.
- **Clear and Direct**: Explain whether the treatment is offered clearly and save it when a match is found.
- **Professional**: Maintain a professional tone throughout the conversation.
- **Step-by-Step Questions**: Ask one question at a time and wait for the response before proceeding to the next. Do not give long or overly detailed answers.

# Task
1. **Identify the Issue**: 
   - Ask the user to describe the dental issue they are experiencing.
   
2. **Match Treatment**: 
   - If the issue matches one of the treatments you offer, save the treatment information using the `save_treatment_tool`.
   - If the treatment is not provided, politely inform the user that the treatment is not available.

3. **Express Empathy**: 
   - Respond to the user’s dental issue with empathy. Example: "I'm sorry to hear about your cavity. We can certainly help with that."

4. **Ask About Appointment**: 
   - After saving the treatment, ask the user if they want to book an appointment for the treatment. Example: "Would you like to book an appointment to address this issue?"If you do not idetify the user tratment then do not suggest him to book appointment.Ask isuue type question for get the user tratment type.

5. **Transfer The Call**: 
   - If the user confirms they want to book an appointment, transfer the call to the appointment booking assistant. 
   - If the user confirms they want to change their treatment, transfer the call to the change treatment tool.

6. **Change The Saved Treatment**:
    - If the user wants to change the saved treatment, follow these three steps:
    - Show the user their currently saved treatment. Example: "Your current saved treatment is [saved_treatment]."
    
    - List all the available treatment options. Example: 
      - "Here are the available treatments you can choose from:"
        - Treatment Name: "Cavity Filling", Problem Description: "For treating cavities caused by tooth decay."
        - Treatment Name: "Teeth Cleaning", Problem Description: "For professional dental cleaning and plaque removal."
        - Treatment Name: "Root Canal", Problem Description: "For treating infected or decayed tooth pulp."
        - Treatment Name: "Teeth Whitening", Problem Description: "For cosmetic treatment to whiten teeth."
        - Treatment Name: "Dental Implants", Problem Description: "For replacing missing teeth with implants."
        - Treatment Name: "Braces", Problem Description: "For straightening misaligned teeth."
 
    - Ask the user to specify which new treatment they would like to change to. Example: "Which treatment would you like to change to from the list above?"
    - Once the user selects a new treatment, call the `change_treatment_tool` function to update it.

7. **Manage Return Calls**:
   - If a caller is transferred back to you, continue the conversation to understand their new query and route them accordingly.
   - When user do not need anything else then end the call <end_call>

Note: When User agree to book an appointment then transfer the call to the appointment booking assistent.
"""



appointment_booking_prompt = f"""
# Context
You are Alex, a customer support assistant for SmileBright Dental Clinic, specifically responsible for booking appointments for in-person dental visits. You will also handle transferring calls to the Treatment Agent or Triage Agent when necessary.

# Task
1. **Greet the Customer**: 
   - Start each interaction with a warm and welcoming greeting.

2. **Collect Information**:
   - Ask for the user's **name**, **phone number**, **preferred date**, and **preferred time** for the appointment.
   - **Important**: Collect each piece of information **one at a time**, in the following order:
     1. First, ask for the user's name.
     2. Next, ask for the user's phone number.
     3. Then, ask for the user's preferred appointment date.
     4. Finally, ask for the user's preferred appointment time.
   - **Do not move on to the next question until the current information has been collected and confirmed.**
   - Example: "Could you please provide your name?" (Wait for the response, confirm it, and move on to the next question.)

3. **Handle Incorrect Input**:
   - If the user enters incorrect information (e.g., wrong name, phone number, date, or time), allow the user to correct their mistake.
   - **Ask for the specific input that needs correction** and then confirm the new input with the user.
   - Example: "I understand you would like to correct your phone number. Please provide the correct phone number."
   - After the user provides the correct information, confirm it again: "Thank you for the update. Your phone number is now corrected to [corrected phone number]. Shall we proceed with this information?"

4. **Handle Treatment Changes**:
   - If at any point the user expresses a desire to change or question their selected treatment, transfer the call back to the Treatment Agent for further assistance.

5. **Handle Refusal to Book**:
   - If the user decides not to book the appointment, do not push for the booking. Instead, transfer the call to the Triage Agent to assist them with other options.

6. **Booking Confirmation**:
   - Once all information has been collected (name, phone number, date, and time), confirm the appointment details with the user **before finalizing** the booking.
   - Example: "Thank you for providing the details. Just to confirm, your appointment is scheduled for [date] at [time]. Would you like me to book this appointment for you?"

7. **Handle Input Corrections**:
   - If the user realizes they have entered incorrect information and wants to change it, follow these steps:
     - Ask for the specific detail that needs to be corrected (e.g., name, phone number, date, or time).
     - Confirm the correction with the user before proceeding.
     - Example: "It seems you want to change your appointment time. Please provide the new time."
     - Once the correction is provided, confirm it: "Your appointment time has been updated to [corrected time]. Would you like to proceed with this change?"

8. **Transfer Call**:
   - Once the appointment has been successfully booked, transfer the call to the Triage Agent for any follow-up questions  any other assistance.
   - If user want to change or delete his appointment , then transfer the call to the Appointment Management Agent.

   
When user what to see the availavle time. then show the list:
{{available_time_slots}}

# Style
- **Professional**: Maintain a courteous and respectful demeanor throughout the conversation.
- **Empathetic**: Show empathy toward the user's situation, and make them feel supported.
- **Clear and Concise**: Always be direct and avoid using unnecessary jargon.
- **Step-by-Step Questions**: Ask one question at a time, and do not overwhelm the user with multiple questions at once.

# Guidelines
- **Promptness**: Respond to the customer as soon as possible to avoid delays.
- **Clarity**: Keep your language simple and instructions easy to follow.
- **Professionalism**: Maintain a professional tone, even if the conversation is casual.
- **Avoid Confusion**: If a user provides incorrect information, make sure to ask for clarification and confirm their new input to avoid mistakes.
"""

appointment_management_prompt = """
# Context
You are an Appointment Management Assistant for SmileBright Dental Clinic. Your role is to manage existing appointments by allowing users to change or delete their appointments. You will handle user requests related to appointment changes or deletions by confirming their appointment ID and making the requested changes.You have aslo a importent role to ransfer the call to Treatment Agent or Triage Agent.

# Tasks
1. **Greet the Customer**: Start each interaction with a warm and welcoming greeting.

2. **Identify Request**:
   - If the user wants to **change** their appointment, ask for the appointment ID and then confirm what specific details (date, time) the user wants to change.
   - If the user wants to **delete** their appointment, ask for the appointment ID and confirm the deletion.

3. **Change Appointment Details**:
   - If the user wants to change the appointment details, first ask for the **appointment ID**.
   - After receiving the appointment ID, ask the user which specific detail they want to change (e.g., date, time).
   - Once the user indicates what they want to change, ask for the new value of that specific detail one by one. For example:
     - If they want to change the **date**, ask: "What is the new date for your appointment?"
     - If they want to change the **time**, ask: "What is the new time for your appointment?"
     - If they want to change the **phone number**, ask : "What is the new phone number for your appointment?
   - After collecting the updated details, call the function to change the appointment.If user do not give any deatails to change then do not call the change_appointment fuction.

4. **Delete Appointment**:
   - If the user wants to delete the appointment, first ask for the **appointment ID**.
   - Confirm that they want to delete the appointment, and upon confirmation, call the function to delete the appointment.

5. **Confirm Changes or Deletion**:
   - After changing or deleting the appointment, confirm with the user that the action has been successfully completed.
   - Example: "Your appointment has been updated successfully. Is there anything else I can assist you with today?"

6. **Transfer Call**:
   - Once the appointment has been successfully changed or deleted, transfer the call to the Triage Agent for any follow-up questions  any other assistance.
   - If at any point the user expresses a desire to book an another appointment for new treatment or want to change his appointment treatment,Then transfer the call to the Treatment Agent.
   - If at any point the user expresses a desire to do not like to take this feature or do not want to change something delete or change,Then transfer the call to the Triage Agent.

   - If the user wants to **see available time slots** ,then give this timeslot list:
    {{available_time_slots}}
   - Do not give the time that are not in the list.


# Style
- **Professional**: Maintain a courteous and respectful demeanor.
- **Empathetic**: Show empathy toward the user's needs and ensure they feel supported.
- **Clear and Concise**: Provide simple instructions without using unnecessary jargon.
- **Step-by-Step Questions**: Ask one question at a time and wait for the response before proceeding to the next. Do not give long or overly detailed answers.

# Guidelines
- **Promptness**: Respond to the customer promptly.
- **Clarity**: Keep instructions easy to understand.
- **Professionalism**: Even in casual conversation, maintain professionalism.
"""


change_treatment_tool = [{
    "type": "function",  # Correct tool type
    "function": {
        "name": "change_treatment_tool",
        "description": "Change the saved treatment for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_treatment": {"type": "string", "description": "The new treatment type the user wants to change to."}
            },
            "required": ["new_treatment"],
            "additionalProperties": False
        },
        "strict": True
    }
}]


appointment_delete_tool =[{
    "type": "function",  # Correct tool type
    "function": {
        "name": "delete_appointment_tool",
        "description": "Deletes an appointment based on the provided appointment ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string", "description": "The unique ID of the appointment that the user wants to delete."},
            },
            "required": ["appointment_id"],
            "additionalProperties": False
        },
        "strict": True
    }
}]



appointment_changing_tool = [
{
  "type": "function",
  "function": {
    "name": "change_appointment_tool",
    "description": "Changes the details of an existing appointment based on the provided appointment ID.",
    "parameters": {
      "type": "object",
      "properties": {
        "appointment_id": {
          "type": "string",
          "description": "The unique ID of the appointment that the user wants to change."
        },
        "changing_data": {
          "type": "string",
          "description": "An object containing the new appointment details. It can include one or more of the following details : new_date, new_time, new_phone_number."
        },
      },
      "required": ["appointment_id","changing_data"],  # Only appointment_id is required
      "additionalProperties": False
    },
    "strict": True
  }
}
]




# Appointment booking tool
appointment_tool =[{
    "type": "function",  # Correct tool type
    "function": {
        "name": "appointment_tool",
        "description": "Book an appointment by providing name, phone number, date, and time.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the person booking the appointment"},
                "phone_number": {"type": "string", "description": "The phone number of the person booking the appointment"},
                "date": {"type": "string", "description": "The date of the appointment (e.g., YYYY-MM-DD)"},
                "time": {"type": "string", "description": "The time of the appointment (e.g., HH:MM)"}
            },
            "required": ["name", "phone_number", "date", "time"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

treatment_saving_tool = [{
    "type": "function",  # Correct tool type
    "function": {
        "name": "save_treatment_tool",
        "description": "Save the treatment information provided by the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "treatment": {"type": "string", "description": "The treatment type the user is receiving"}
            },
            "required": ["treatment"],
            "additionalProperties": False
        },
        "strict": True
    }
},]


triage_tools = [
    {
        "type": "function",
        "function": {
            "name": "send_query_to_agents",
            "description": "Sends the user query to relevant agents based on their capabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "An array of agent names to send the query to."
                    },
                    "query": {
                        "type": "string",
                        "description": "The user query to send."
                    }
                },
                "required": ["agents", "query"]
            }
        },
        "strict": True
    }
]


# Handle user message logic
conversation_messages = []

appointment_database= {}
# Available time slots database (dictionary)
available_time_slots = {
    "2024-08-21": {
        "09:00": True,
        "10:00": True,
        "11:00": True,
        "12:00": True,
        "13:00": True,
        "14:00": True,
        "15:00": True,
    },
    "2024-08-22": {
        "09:00": True,
        "10:00": True,
        "11:00": True,
        "12:00": True,
        "13:00": True,
        "14:00": True,
        "15:00": True,
    },
    # Add more dates and times as needed
}

# Function to check if a slot is available
def check_slot_availability(date, time):
    if date in available_time_slots and time in available_time_slots[date]:
        return available_time_slots[date][time]
    else:
        return False

# Function to book a slot
def book_slot(date, time):
    if check_slot_availability(date, time):
        available_time_slots[date][time] = False
        print(f"Slot booked: {date} at {time}")
    else:
        print(f"Slot not available: {date} at {time}")


def generate_appointment_id(phone_number, date, time):
    return f"{phone_number}_{date}_{time}"

def save_appointment(name, phone_number, date, time, treatment):
    # Generate a unique appointment ID
    appointment_id = generate_appointment_id(phone_number, date, time)
    
    # Save the appointment data to the database
    appointment_database[appointment_id] = {
        "name": name,
        "phone_number": phone_number,
        "date": date,
        "time": time,
        "treatment": treatment
    }
    
    print(f"Appointment saved for {name} on {date} at {time}")
    return appointment_id

treatment_data_store = []
# Tool execution logic
def execute_tool(tool_calls, messages):
    global conversation_messages
    global treatment_data_store

    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_arguments = json.loads(tool_call.function.arguments)
        #print(tool_arguments)
        if tool_name == 'save_treatment_tool':
            treatment = tool_arguments.get("treatment")
            treatment_data_store.append(treatment)
            #print(f"Saved treatment: {treatment}")
            query = f"Saved treatment: {treatment}.I'm sorry to hear about your issue. Now that we've identified your treatment, would you like to book an appointment?"
            conversation_messages.append({"role": "assistant", "content": query})
            print(query)

        elif tool_name == "appointment_tool":
            # Extract the date and time from the tool arguments
            name = tool_arguments["name"]
            phone_number = tool_arguments["phone_number"]
            date = tool_arguments["date"]
            time = tool_arguments["time"]

            # Check if the slot is available before booking
            if check_slot_availability(date, time):
                # Book the slot by marking it as False (booked)
                book_slot(date, time)
                
                # Save the appointment to the database
                treatment = treatment_data_store[-1] if treatment_data_store else "Unknown Treatment"
                appointment_id = save_appointment(name, phone_number, date, time, treatment)
                query = f"Appointment booked successfully for {name} on {date} at {time}. Your appointment ID is {appointment_id}.Are you need anything else?"
                # Log the appointment details
                print(query)
                

                # Append the appointment confirmation to the messages
                messages.append({
                    "role": "assistant",
                    "content": query
                })
            else:
                query = f"Sorry, the time slot {time} on {date} is unavailable. Please choose another time."
                # Inform the user that the selected slot is unavailable
                print(query)
                messages.append({
                    "role": "assistant", 
                    "content": query
                })

        elif tool_name == "delete_appointment_tool":
            appointment_id = tool_arguments["appointment_id"]
            if appointment_id in appointment_database:
                del appointment_database[appointment_id]
                query = f"Appointment {appointment_id} deleted successfully. Do you need anything else?"
                print(query)
                messages.append({
                    "role": "assistant",
                    "content":query
                })
            else:
                query = f"Appointment ID {appointment_id} not found. Please provide a valid appointment ID."
                print(query)
                messages.append({
                    "role": "assistant",
                    "content": query
                })

        elif tool_name == "change_appointment_tool":
            appointment_id = tool_arguments["appointment_id"]
            new_details = json.loads(tool_arguments["changing_data"])  # Parse the JSON string to a dictionary
            
            # Assuming you want to update the appointment with new details
            if appointment_id in appointment_database:
                appointment = appointment_database[appointment_id]
                
                # Check if the new date is provided
                if "new_date" in new_details:
                    new_date = new_details["new_date"]
                    current_time = appointment["time"]  # Keep the existing time
                    
                    # Check if the new date and current time is available
                    if check_slot_availability(new_date, current_time):
                        appointment["date"] = new_date
                        query = f"Appointment {appointment_id} date updated to {new_date}. Do you need anything else?"
                        print(query)
                        messages.append({
                            "role": "assistant",
                            "content": query
                        })
                    else:
                        query = f"Sorry, the current time slot {current_time} on the new date {new_date} is unavailable.Please provide a another date."
                        print(query)
                        messages.append({
                            "role": "assistant",
                            "content": query
                        })
                
                # Check if the new time is provided
                if "new_time" in new_details:
                    new_time = new_details["new_time"]
                    current_date = appointment["date"]  # Keep the existing date
                    
                    # Check if the new time and current date is available
                    if check_slot_availability(current_date, new_time):
                        appointment["time"] = new_time
                        query = f"Appointment {appointment_id} time updated to {new_time}. Do you need anything else?"
                        print(query)
                        messages.append({
                            "role": "assistant",
                            "content": query
                        })
                    else:
                        query = f"Sorry, the time slot {new_time} on the current date {current_date} is unavailable.Please provide a another time."
                        print(query)
                        messages.append({
                            "role": "assistant",
                            "content": query
                        })

                #print(f"Appointment {appointment_id} updated successfully. Do you need anything else?")
            else:
                query = f"Appointment ID {appointment_id} not found. Please provide a valid appointment ID."
                print(query)
                messages.append({
                    "role": "assistant",
                    "content": query
                })

        elif tool_name == 'change_treatment_tool':
                new_treatment = tool_arguments.get("new_treatment")
                treatment_data_store[-1] = new_treatment  # Update the last saved treatment
                query = f"Your treatment has been changed to {new_treatment}.Now that we've identified your treatment, would you like to book an appointment for this treatment?"
                print(query)
                messages.append({"role": "assistant", "content": query})
    return query


# Handle appointment booking logic
def handle_appointment_management_agent(query, conversation_messages):
    global current_agent
    messages = [{"role": "system", "content": appointment_management_prompt}]
    conversation_messages.append({"role": "user", "content": query})
    messages.extend(conversation_messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        tools=appointment_delete_tool+appointment_changing_tool+triage_tools,
    )

    if response.choices[0].message.content is not None:
        print(response.choices[0].message.content)
        conversation_messages.append({"role": "assistant", "content": response.choices[0].message.content})
        
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.function.name == 'delete_appointment_tool' or "change_appointment_tool":
                return execute_tool([tool_call], conversation_messages)
            

            elif tool_call.function.name == 'send_query_to_agents':
                agents = json.loads(tool_call.function.arguments)['agents']
                query = json.loads(tool_call.function.arguments)['query']
                #print(query)
                for agent in agents:
                    if agent == "Treatment Agent":
                        print("Routing to Treatment Agent...")
                        current_agent = "TreatmentAgent"
                        return handle_treatment_agent(query, conversation_messages) # Exit after routing

                    elif agent == "Triage Agent":
                        current_agent = "TrigeAgent"
                        print("Routing to Triage Agent...")
                        return handle_user_message(query) # Exit after routing
    return response.choices[0].message.content


# Handle appointment booking logic
def handle_appointment_booking_agent(query, conversation_messages):
    global current_agent
    messages = [{"role": "system", "content": appointment_booking_prompt}]
    conversation_messages.append({"role": "user", "content": query})
    messages.extend(conversation_messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        tools=appointment_tool + triage_tools,
    )
    if response.choices[0].message.content is not None:
        print(response.choices[0].message.content)
        conversation_messages.append({"role": "assistant", "content": response.choices[0].message.content})
        
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.function.name == 'appointment_tool':
                return execute_tool([tool_call], conversation_messages) # Exit after handling

            elif tool_call.function.name == 'send_query_to_agents':
                agents = json.loads(tool_call.function.arguments)['agents']
                query = json.loads(tool_call.function.arguments)['query']
                for agent in agents:
                    if agent == "Treatment Agent":
                        print("Routing to Treatment Agent...")
                        current_agent = "TreatmentAgent"
                        return handle_treatment_agent(query, conversation_messages) # Exit after routing

                    elif agent == "Triage Agent":
                        current_agent = "TrigeAgent"
                        print("Routing to Triage Agent...")
                        return handle_user_message(query) # Exit after routing
                    elif agent == "Appointment Management Agent":
                        print("Routing to Appointment Management Agent...")
                        current_agent = "AppointmentManagementAgent"
                        return handle_appointment_management_agent(query,conversation_messages)

    return response.choices[0].message.content


# Handle treatment agent logic
def handle_treatment_agent(query, conversation_messages):
    global current_agent
    messages = [{"role": "system", "content": treatment_agent}]
    conversation_messages.append({"role": "user", "content": query})
    messages.extend(conversation_messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        tools=treatment_saving_tool + triage_tools+ change_treatment_tool,
    )
    if response.choices[0].message.content is not None:
        print(response.choices[0].message.content)
        conversation_messages.append({"role": "assistant", "content": response.choices[0].message.content})
        
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            #print(tool_call.function.name)
            if tool_call.function.name == 'save_treatment_tool' or tool_call.function.name == 'change_treatment_tool':
                return execute_tool([tool_call], conversation_messages)
                
            elif tool_call.function.name == 'send_query_to_agents':
                agents = json.loads(tool_call.function.arguments)['agents']
                query = json.loads(tool_call.function.arguments)['query']
                for agent in agents:
                    if agent == "appointment booking assistant":
                        print("Routing to Appointment Booking Agent...")
                        current_agent = "AppointmentBookingAgent"
                        return handle_appointment_booking_agent(query, conversation_messages) # Exit after routing

                    elif agent == "Triage Agent":
                        current_agent = "TrigeAgent"
                        print("Routing to Triage Agent...")
                        return handle_user_message(query) # Exit after routing
                    elif agent == "Appointment Management Agent":
                        print("Routing to Appointment Management Agent...")
                        current_agent = "AppointmentManagementAgent"
                        return handle_appointment_management_agent(query,conversation_messages)
                    
    return response.choices[0].message.content


def handle_user_message(user_query):
    global current_agent
    global conversation_messages

    user_message = {"role": "user", "content": user_query}
    conversation_messages.append(user_message)

    messages = [{"role": "system", "content": triaging_system_prompt}]
    messages.extend(conversation_messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        tools=triage_tools,
    )
    if response.choices[0].message.content is not None:
        print(response.choices[0].message.content)
        conversation_messages.append({"role": "assistant", "content": response.choices[0].message.content})

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.function.name == 'send_query_to_agents':
                agents = json.loads(tool_call.function.arguments)['agents']
                query = json.loads(tool_call.function.arguments)['query']
                
                #print(query)
                for agent in agents:
                    if agent == "Treatment Agent":
                        print("Routing to Treatment Agent...")
                        current_agent = "TreatmentAgent"
                        
                        return  handle_treatment_agent(query, conversation_messages)

                    elif agent == "Troubleshooting Agent":
                        print("Routing to Troubleshooting Agent...")
                        return  # Exit after routing
                    elif agent == "Appointment Management Agent":
                        print("Routing to Appointment Management Agent...")
                        current_agent = "AppointmentManagementAgent"
                        return handle_appointment_management_agent(query,conversation_messages)
                    
    return response.choices[0].message.content

# Example usage:
#handle_user_message("give your introduction in short")
#while True:




#--end--



app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/chatgpt"

@app.route("/")
def home():

    return render_template("index.html")

@app.route("/api", methods=["GET", "POST"])
def qa():
    if request.method == "POST":
        #print(request.json)
        question = request.json.get("question")
        
        print(question)
        
        
        if current_agent == "TrigeAgent":
            data = {"question": question, "answer": handle_user_message(question)}

        elif current_agent == "AppointmentBookingAgent":
            data = {"question": question, "answer": handle_appointment_booking_agent(question, conversation_messages)}

        elif current_agent == "TreatmentAgent":
            data = {"question": question, "answer": handle_treatment_agent(question, conversation_messages)}


        elif current_agent == "AppointmentManagementAgent":
            data = {"question": question, "answer": handle_appointment_management_agent(question,conversation_messages)
}

        #print(response)
        return jsonify(data)
    data = {"result": "Thank you! I'm just a machine learning model designed to respond to questions and generate text based on my training data. Is there anything specific you'd like to ask or discuss? "}
        
    return jsonify(data)

app.run(debug=True, port=5001)