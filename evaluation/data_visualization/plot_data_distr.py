import matplotlib.pyplot as plt

# Example dataset with counts for each class
# data = {'Benign': 2273097, 'Malicious': 557646}
data = {'Benign': 11367, 'Malicious': 2791}# Labels and values
labels = list(data.keys())
values = list(data.values())

# Colors for the chart
colors = ['#4CAF50', '#FF6347']  # Green for benign, red for malicious

# Create a pie chart
fig, ax = plt.subplots()
ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, explode=(0.1, 0), shadow=True)

# Equal aspect ratio ensures the pie chart is drawn as a circle.
ax.axis('equal')

# Add a title
plt.title('Distribution of Benign and Malicious Requests for Slips')

# Save as SVG
plt.savefig('/mnt/c/Users/Max/Desktop/CIC-IDS-Slips-Class-Distribtion.svg', format='svg')